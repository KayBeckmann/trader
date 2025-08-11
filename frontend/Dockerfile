FROM node:18-alpine

WORKDIR /app

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application source code
COPY . .

# Expose the Vite port
EXPOSE 5173

# Run the Vite dev server. 
# The --host flag is crucial to expose the server to the host machine from inside the container.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]