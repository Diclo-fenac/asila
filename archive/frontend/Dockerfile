FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package.json and install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy the rest of the application
COPY . .

# Expose Vite's default port
EXPOSE 5173

# Start the Vite development server and expose on all interfaces
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
