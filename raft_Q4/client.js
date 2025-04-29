// client.js
const grpc        = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

if (process.argv.length < 4) {
  console.error('Usage: node client.js <nodeAddr> <operation>');
  process.exit(1);
}

const [,, nodeAddr, operation] = process.argv;

// load raft.proto
const packageDef = protoLoader.loadSync('raft.proto');
const raftProto  = grpc.loadPackageDefinition(packageDef).raft;

// make a ClientService stub against the given node
const client = new raftProto.ClientService(
  nodeAddr,
  grpc.credentials.createInsecure()
);

console.log(`Client sends RPC Execute to Node ${nodeAddr}`);
client.Execute({ operation }, (err, resp) => {
  if (err) {
    console.error('RPC error:', err);
    process.exit(1);
  }
  console.log('Client got response:', resp);
});