FROM node:20-alpine
WORKDIR /app
COPY moltbot_bridge/package.json moltbot_bridge/tsconfig.json /app/
RUN npm install && npm cache clean --force
COPY moltbot_bridge/src /app/src
RUN npx tsc -p .
EXPOSE 8080
CMD ["node", "dist/index.js"]
