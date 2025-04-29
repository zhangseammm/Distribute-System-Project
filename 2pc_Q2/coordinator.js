// coordinator.js
const grpc       = require('@grpc/grpc-js');
const loader     = require('@grpc/proto-loader');
const packageDef = loader.loadSync('two_pc.proto');
const proto      = grpc.loadPackageDefinition(packageDef).twopc;

const me          = process.env.NAME;
const participants= process.env.PARTICIPANTS.split(',')  // e.g. "part1:50051:50061,part2:50051:50061..."
  .map(p=>{
    const [name, vport, dport] = p.split(':');
    return { name, vaddr:`${name}:${vport}`, daddr:`${name}:${dport}` };
  });

async function votePhase(tx) {
  const votes = [];
  for (const p of participants) {
    console.log(`Phase Voting of Node ${me} sends RPC Vote to Phase Voting of Node ${p.name}`);
    const client = new proto.Participant(p.vaddr, grpc.credentials.createInsecure());
    await new Promise((res, rej)=>{
      client.Vote({ transaction_id: tx }, (e, resp)=>{
        if (e) return rej(e);
        console.log(`Phase Voting of Node ${me} got ${resp.vote} from ${p.name}`);
        votes.push(resp.vote);
        res();
      });
    });
  }
  return votes;
}

async function decisionPhase(tx, votes) {
  const allCommit = votes.every(v=>v===proto.VoteResponse.COMMIT);
  const decision = allCommit
    ? proto.DecisionRequest.COMMIT
    : proto.DecisionRequest.ABORT;

  for (const p of participants) {
    console.log(`Phase Decision of Node ${me} sends RPC Decide to Phase Decision of Node ${p.name}`);
    const client = new proto.DecisionParticipant(p.daddr, grpc.credentials.createInsecure());
    await new Promise((res, rej)=>{
      client.Decide({ transaction_id: tx, decision }, (e, ack)=>{
        if (e) return rej(e);
        console.log(`Phase Decision of Node ${me} got ack from ${p.name}`);
        res();
      });
    });
  }
}

(async ()=>{
  const tx = `tx-${Date.now()}`;
  console.log(`[Coordinator] starting tx ${tx}`);
  const votes = await votePhase(tx);
  await decisionPhase(tx, votes);
  console.log(`[Coordinator] done.`);
})();