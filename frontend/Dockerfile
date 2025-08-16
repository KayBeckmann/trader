FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
# Install dependencies during build
RUN npm install
COPY . .
EXPOSE 5173
# On container start, ensure dependencies are installed, then run the dev server
CMD ["/bin/sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"]
