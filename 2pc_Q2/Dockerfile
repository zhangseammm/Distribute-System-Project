# Dockerfile
FROM node:16-slim

# install Python
RUN apt-get update && apt-get install -y python3 python3-pip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY package.json package-lock.json two_pc.proto ./
RUN npm install \
 && pip3 install grpcio grpcio-tools \
 && python3 -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. two_pc.proto

COPY *.js *.py ./

# entrypoint: ROLE=coordinator or participant
ENTRYPOINT ["sh","-c", "\
  if [ \"$ROLE\" = \"coordinator\" ]; then \
    node coordinator.js; \
  else \
    python3 participant.py & \
    node decision.js; \
  fi \
"]