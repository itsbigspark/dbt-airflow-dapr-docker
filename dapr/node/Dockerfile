FROM node:14-alpine 
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000 3001 3002
CMD ["sh", "-c", "node audit-service.js & node airflow-trigger-service.js & node airflow-config-service.js"]

