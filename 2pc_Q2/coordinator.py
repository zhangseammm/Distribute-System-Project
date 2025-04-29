# coordinator.py
import grpc
import two_pc_pb2
import two_pc_pb2_grpc
import os
import time

def collect_votes(participants, tx_id):
    votes = []
    for name, addr in participants.items():
        with grpc.insecure_channel(addr) as ch:
            stub = two_pc_pb2_grpc.ParticipantStub(ch)
            resp = stub.Vote(two_pc_pb2.VoteRequest(transaction_id=tx_id))
            print(f"[Coordinator] {name} voted {'COMMIT' if resp.vote==resp.COMMIT else 'ABORT'}")
            votes.append(resp.vote)
    return votes

if __name__ == "__main__":
    # Expect PARTICIPANTS env var: comma-sep list name:host:port
    raw = os.getenv("PARTICIPANTS", "")
    participants = {}
    for entry in raw.split(","):
        if not entry: continue
        name, host, port = entry.split(":")
        participants[name] = f"{host}:{port}"

    tx_id = f"tx-{int(time.time())}"
    print(f"[Coordinator] Starting vote phase for {tx_id}")
    votes = collect_votes(participants, tx_id)

    if all(v==two_pc_pb2.VoteResponse.COMMIT for v in votes):
        print("[Coordinator] All participants COMMIT → sending global COMMIT")
    else:
        print("[Coordinator] At least one ABORT → sending global ABORT")