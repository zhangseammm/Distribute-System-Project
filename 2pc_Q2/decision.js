// decision.js
const grpc      = require('@grpc/grpc-js');
const loader    = require('@grpc/proto-loader');
const packageDef= loader.loadSync('two_pc.proto');
const proto     = grpc.loadPackageDefinition(packageDef).twopc;

const nodeId    = process.env.NAME;
const PY_ADDR   = `localhost:50051`;      // local Python server
const DEC_PORT  = process.env.DECISION_PORT || 50061;

function Decide(call, callback) {
  const { transaction_id, decision } = call.request;
  console.log(`Phase Decision of Node ${nodeId} received RPC Decide → calling Python GlobalDecision`);
  // call back into Python to apply
  const pyClient = new proto.Participant(PY_ADDR, grpc.credentials.createInsecure());
  console.log(`Phase Decision of Node ${nodeId} sends RPC GlobalDecision to Phase Decision of Node ${nodeId}`);
  pyClient.GlobalDecision({ transaction_id, decision }, (err, ack) => {
    if (err) return callback(err);
    callback(null, { success: ack.success });
  });
}

function main() {
  const server = new grpc.Server();
  server.addService(proto.DecisionParticipant.service, { Decide });
  server.bindAsync(`0.0.0.0:${DEC_PORT}`, grpc.ServerCredentials.createInsecure(), () => {
    server.start();
    console.log(`[Node] DecisionParticipant server up on ${DEC_PORT}`);
  });
}

main();