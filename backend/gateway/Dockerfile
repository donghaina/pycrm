FROM node:20-alpine
WORKDIR /app
COPY package.json /app/package.json
RUN npm install
COPY src /app/src
EXPOSE 4000
CMD ["npm", "start"]
