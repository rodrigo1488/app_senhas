FROM node:20-alpine
WORKDIR /app
RUN apk add --no-cache git python3 make g++
COPY package.json ./
RUN npm install --omit=dev
COPY server.js ./
RUN mkdir -p /data/auth
ENV PORT=3001
ENV AUTH_DIR=/data/auth
EXPOSE 3001
CMD ["npm", "start"]
