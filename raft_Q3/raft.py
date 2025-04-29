import grpc, threading, time, random, os
from concurrent import futures

import raft_pb2, raft_pb2_grpc

class RaftNode(raft_pb2_grpc.RaftServicer):
    def __init__(self, node_id, peers):
        self.id = node_id
        self.peers = peers                # [(peer_id, addr), ...]
        self.state = "Follower"
        self.current_term = 0
        self.voted_for = None
        self.votes_received = set()
        self.lock = threading.Lock()

        # used to reset election timer
        self.election_event = threading.Event()
        threading.Thread(target=self._election_timer, daemon=True).start()

    # ─── RPC Handlers ────────────────────────────────────────────────────────────

    def RequestVote(self, req, ctx):
        print(f"Node {self.id} runs RPC RequestVote called by Node {req.candidateId}")
        with self.lock:
            if req.term < self.current_term:
                return raft_pb2.RequestVoteResponse(term=self.current_term, voteGranted=False)

            if req.term > self.current_term:
                self.current_term = req.term
                self.state = "Follower"
                self.voted_for = None

            grant = False
            if self.voted_for in (None, req.candidateId):
                self.voted_for = req.candidateId
                grant = True
                self._reset_election_timer()

            return raft_pb2.RequestVoteResponse(term=self.current_term, voteGranted=grant)

    def AppendEntries(self, req, ctx):
        print(f"Node {self.id} runs RPC AppendEntries called by Node {req.leaderId}")
        with self.lock:
            if req.term < self.current_term:
                return raft_pb2.AppendEntriesResponse(term=self.current_term, success=False)
            # valid heartbeat
            self.current_term = req.term
            self.state = "Follower"
            self.voted_for = None
            self._reset_election_timer()
            return raft_pb2.AppendEntriesResponse(term=self.current_term, success=True)

    # ─── Election Timer ──────────────────────────────────────────────────────────

    def _election_timer(self):
        while True:
            timeout = random.uniform(1.5, 3.0)
            fired = self.election_event.wait(timeout)
            if not fired:
                self._start_election()
            self.election_event.clear()

    def _reset_election_timer(self):
        self.election_event.set()

    # ─── Election Logic ──────────────────────────────────────────────────────────

    def _start_election(self):
        with self.lock:
            self.state = "Candidate"
            self.current_term += 1
            self.voted_for = self.id
            self.votes_received = {self.id}
            term = self.current_term
        print(f"Node {self.id} becomes Candidate for term {term}")
        for peer_id, addr in self.peers:
            threading.Thread(target=self._send_request_vote, args=(peer_id, addr, term), daemon=True).start()

    def _send_request_vote(self, peer_id, addr, term):
        print(f"Node {self.id} sends RPC RequestVote to Node {peer_id}")
        stub = raft_pb2_grpc.RaftStub(grpc.insecure_channel(addr))
        try:
            resp = stub.RequestVote(raft_pb2.RequestVoteRequest(term=term, candidateId=self.id))
            with self.lock:
                if resp.voteGranted and self.state=="Candidate" and resp.term==self.current_term:
                    self.votes_received.add(peer_id)
                if len(self.votes_received) > len(self.peers)//2:
                    self._become_leader()
        except Exception:
            pass

    def _become_leader(self):
        if self.state!="Candidate": return
        self.state = "Leader"
        print(f"Node {self.id} becomes Leader for term {self.current_term}")
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def _heartbeat_loop(self):
        while True:
            with self.lock:
                if self.state!="Leader": return
                term = self.current_term
            for peer_id, addr in self.peers:
                print(f"Node {self.id} sends RPC AppendEntries to Node {peer_id}")
                stub = raft_pb2_grpc.RaftStub(grpc.insecure_channel(addr))
                try:
                    stub.AppendEntries(raft_pb2.AppendEntriesRequest(term=term, leaderId=self.id))
                except Exception:
                    pass
            time.sleep(1.0)  # heartbeat interval

# ─── Startup ────────────────────────────────────────────────────────────────────

def serve():
    node_id = os.getenv("NODE_ID")
    peers_raw = os.getenv("PEERS","").split(",")
    peers = []
    for entry in peers_raw:
        if not entry: continue
        peer_id, host, port = entry.split(":")
        # skip yourself
        if peer_id == node_id:
            continue
        # reassemble the host:port address
        addr = f"{host}:{port}"
        peers.append((peer_id, addr))


    server = grpc.server(futures.ThreadPoolExecutor())
    raft_pb2_grpc.add_RaftServicer_to_server(RaftNode(node_id, peers), server)
    server.add_insecure_port("[::]:5000")
    server.start()
    print(f"[{node_id}] Raft node up on 5000 (state=Follower)")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()