# participant.py
import grpc
from concurrent import futures
import os, time, random

import two_pc_pb2, two_pc_pb2_grpc

class ParticipantServicer(two_pc_pb2_grpc.ParticipantServicer):
    def Vote(self, request, context):
        tx = request.transaction_id
        decision = random.choice([
            two_pc_pb2.VoteResponse.COMMIT,
            two_pc_pb2.VoteResponse.ABORT
        ])
        print(f"Phase Voting of Node {os.getenv('NAME')} received RPC Vote → returning {decision}")
        return two_pc_pb2.VoteResponse(vote=decision)

    def GlobalDecision(self, request, context):
        tx, dec = request.transaction_id, request.decision
        action = "COMMIT" if dec == two_pc_pb2.DecisionRequest.COMMIT else "ABORT"
        print(f"Phase Decision of Node {os.getenv('NAME')} received RPC GlobalDecision → {action} locally")
        # here you’d apply your local commit/abort
        return two_pc_pb2.DecisionAck(success=True)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(4))
    two_pc_pb2_grpc.add_ParticipantServicer_to_server(ParticipantServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print(f"[Python] Voting+GlobalDecision server up on 50051")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()