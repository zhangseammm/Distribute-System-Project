## All docker containers have been warpped up.

1. Implement the voting phase of 2PC, using python

```
python -m grpc_tools.protoc --proto_path=proto --python_out=. --grpc_python_out=. proto/twopc.proto

docker-compose up --build

```

2. Implement the decision phase of 2PC, using node langauge

```
docker-compose up --build
```

3. Implement the leader election of a simplified version of Raft, using python.

```
docker-compose up --build
```

4. Implement the log replication of a simplified version of Raft, using node langauge.

```
# run 5 server node
docker-compose up --build

# run client
node client.js 0.0.0.0:5001 "doSomething"
node client.js 0.0.0.0:5001 "doSomething1"
node client.js 0.0.0.0:5001 "doSomething2"
```

