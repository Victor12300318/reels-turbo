FROM node:18-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

ENV HOSTNAME="0.0.0.0"
ENV PORT=3000

EXPOSE 3000
EXPOSE 3008

CMD ["npm", "run", "dev"]
