const grpc        = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

// load the compiled proto
const packageDef = protoLoader.loadSync('raft.proto');
const raftProto  = grpc.loadPackageDefinition(packageDef).raft;

// Environment
const NODE_ID    = process.env.NODE_ID;
const LEADER_ID  = process.env.LEADER_ID;
const PEERS      = (process.env.PEERS || "")
  .split(',')
  .filter(e => e)
  .map(e => {
    const [id, host, port] = e.split(':');
    return { id, addr: `${host}:${port}` };
  })
  .filter(p => p.id !== NODE_ID);

// In-memory Raft state
let logEntries    = [];  // array of LogEntry
let commitIndex   = 0;   // index of last committed entry
let executedIndex = 0;   // index up to which we've executed

//
// ─── RPC Handlers ────────────────────────────────────────────────────────────
//

// Follower & leader both expose AppendEntries
function AppendEntries(call, callback) {
  const { leaderId, entries, commitIndex: cIdx } = call.request;
  console.log(`Node ${NODE_ID} runs RPC AppendEntries called by Node ${leaderId}`);

  // replace local log
  logEntries = entries;

  // execute any newly committed entries up to cIdx
  for (let i = executedIndex; i < cIdx; i++) {
    const e = logEntries[i];
    console.log(`Node ${NODE_ID} executes operation ${e.operation} at index ${e.index}`);
  }
  executedIndex = Math.max(executedIndex, cIdx);

  callback(null, { term: 0, success: true });
}

// ClientService for Execute(op)
function Execute(call, callback) {
  console.log(`Node ${NODE_ID} runs RPC Execute called by Client`);

  // if not leader, forward
  if (NODE_ID !== LEADER_ID) {
    console.log(`Node ${NODE_ID} sends RPC Execute to Node ${LEADER_ID}`);
    const client = new raftProto.ClientService(
      `${LEADER_ID}:5000`,
      grpc.credentials.createInsecure()
    );
    // server‐side log at leader
    console.log(`Node ${LEADER_ID} runs RPC Execute called by Node ${NODE_ID}`);
    return client.Execute(call.request, callback);
  }

  // ─── we are leader ─────────────────────────────────────────────────────────
  const { operation } = call.request;
  console.log(`Node ${NODE_ID} appends operation ${operation}`);
  const newIndex = logEntries.length + 1;
  const entry = { index: newIndex, timestamp: Date.now(), operation };
  logEntries.push(entry);

  // multicast AppendEntries to followers
  let ackCount = 1; // count self
  const cIdx     = commitIndex;

  const acks = PEERS.map(peer => new Promise(res => {
    console.log(`Node ${NODE_ID} sends RPC AppendEntries to Node ${peer.id}`);
    const client = new raftProto.Raft(
      peer.addr,
      grpc.credentials.createInsecure()
    );
    client.AppendEntries(
      { term: 0, leaderId: NODE_ID, entries: logEntries, commitIndex: cIdx },
      (err, resp) => {
        if (!err && resp.success) ackCount++;
        res();
      }
    );
  }));

  Promise.all(acks).then(() => {
    // once a majority has ACKed
    if (ackCount > (PEERS.length + 1) / 2) {
      // execute all pending entries
      for (let i = commitIndex; i < logEntries.length; i++) {
        const e = logEntries[i];
        console.log(`Node ${NODE_ID} executes operation ${e.operation} at index ${e.index}`);
      }
      commitIndex = logEntries.length;
    }

    // reply to client
    callback(null, {
      success: true,
      result: `Operation ${operation} executed`,
    });
  });
}

//
// ─── Server setup ─────────────────────────────────────────────────────────────
//
function main() {
  const server = new grpc.Server();
  server.addService(raftProto.Raft.service, { AppendEntries });
  server.addService(raftProto.ClientService.service, { Execute });
  server.bindAsync(
    '0.0.0.0:5000',
    grpc.ServerCredentials.createInsecure(),
    () => {
      server.start();
      console.log(`Node ${NODE_ID} listening on 5000  (leader=${LEADER_ID})`);
    }
  );
}

main();