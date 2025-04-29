import os, time, random
from concurrent import futures
import grpc

import twopc_pb2, twopc_pb2_grpc

class ParticipantServicer(twopc_pb2_grpc.TwoPCServicer):
    def __init__(self, replica_id):
        self.replica_id = replica_id

    def Vote(self, request, context):
        # Simple logic: randomly commit or abort
        decision = random.choice([
            twopc_pb2.VoteReply.VOTE_COMMIT,
            twopc_pb2.VoteReply.VOTE_ABORT
        ])
        print(f"[{self.replica_id}] Received vote request for tx={request.transaction_id}, replying {decision}")
        return twopc_pb2.VoteReply(
            decision=decision,
            replica_id=self.replica_id
        )

def serve_participant(port, replica_id):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    twopc_pb2_grpc.add_TwoPCServicer_to_server(
        ParticipantServicer(replica_id), server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"[{replica_id}] Participant listening on port {port}")
    server.wait_for_termination()

def run_coordinator(participants, tx_id="coordinator1"):
    # Wait a moment for participants to come up
    time.sleep(5)
    stubs = []
    for addr in participants:
        ch = grpc.insecure_channel(addr)
        stubs.append(twopc_pb2_grpc.TwoPCStub(ch))

    print("[coordinator] Sending VoteRequest to all participants")
    req = twopc_pb2.VoteRequest(transaction_id=tx_id)

    replies = []
    for stub in stubs:
        try:
            r = stub.Vote(req, timeout=3)
        except grpc.RpcError as e:
            print("[coordinator] RPC failed:", e)
            r = None
        replies.append(r)

    commits = [r for r in replies if r and r.decision == twopc_pb2.VoteReply.VOTE_COMMIT]
    aborts  = [r for r in replies if r and r.decision == twopc_pb2.VoteReply.VOTE_ABORT]

    print(f"[coordinator] votes → commit:{len(commits)} abort:{len(aborts)}")
    if aborts:
        print("[coordinator] -> ABORT transaction")
    else:
        print("[coordinator] -> COMMIT transaction")

def main():
    role = os.getenv("ROLE")
    if role == "participant":
        replica_id = os.getenv("REPLICA_ID")
        port       = os.getenv("PORT")
        serve_participant(port, replica_id)

    elif role == "coordinator":
        participants = os.getenv("PARTICIPANTS").split(",")
        run_coordinator(participants)

    else:
        print("ERROR: set ROLE=participant or ROLE=coordinator")

if __name__ == "__main__":
    main()