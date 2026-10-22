# Multi-stage production build for Person C React dashboard
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies first for Docker caching
COPY package.json package-lock.json ./
RUN npm ci || npm install

# Build production Vite bundle
COPY . .
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Serve with lightweight Alpine Nginx
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
