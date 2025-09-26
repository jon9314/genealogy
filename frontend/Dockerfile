# Build stage: bundle the Vite frontend
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies separately to leverage Docker layer caching
COPY package.json ./
RUN npm install --legacy-peer-deps

# Copy the rest of the source and build the production bundle
COPY . .
RUN npm run build

# Runtime stage: serve the built assets through Nginx
FROM nginx:1.25-alpine AS runtime

# Allow larger uploads for PDF processing through the proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
