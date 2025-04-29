FROM node:16-slim

WORKDIR /app
COPY package.json package-lock.json raft.proto ./
RUN npm install

COPY log_replication.js ./

EXPOSE 5000
CMD ["node", "log_replication.js"]