FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt raft.proto ./
RUN pip install --no-cache-dir -r requirements.txt \
 && python -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. raft.proto

COPY raft.py ./

ENV PYTHONUNBUFFERED=1

CMD ["python", "raft.py"]