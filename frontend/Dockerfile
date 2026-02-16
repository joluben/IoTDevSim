# ═══════════════════════════════════════════════════════════════════
# IoT-DevSim Frontend - Production Dockerfile
# ═══════════════════════════════════════════════════════════════════
# Multi-stage build:
#   1. Build stage: Compiles the React app with Vite
#   2. Production stage: Serves static files with nginx
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# STAGE 1: Build
# ═══════════════════════════════════════════════════════════════════
FROM node:20-alpine AS builder

# Build-time arguments for Vite environment variables
ARG VITE_API_URL
ARG VITE_WS_URL
ARG VITE_ENVIRONMENT

# Make them available as environment variables during build
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_WS_URL=${VITE_WS_URL}
ENV VITE_ENVIRONMENT=${VITE_ENVIRONMENT}

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build for production
# Vite will use the environment variables set above
RUN npm run build

# ═══════════════════════════════════════════════════════════════════
# STAGE 2: Production - Nginx
# ═══════════════════════════════════════════════════════════════════
FROM nginx:alpine

# Install security updates
RUN apk update && apk upgrade && apk add --no-cache curl

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy built app from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create non-root user for nginx
RUN addgroup -g 1001 -S nginx-group && \
    adduser -u 1001 -S nginx-user -G nginx-group

# Set proper permissions
RUN chown -R nginx-user:nginx-group /usr/share/nginx/html && \
    chown -R nginx-user:nginx-group /var/cache/nginx && \
    chown -R nginx-user:nginx-group /var/log/nginx && \
    chown -R nginx-user:nginx-group /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx-user:nginx-group /var/run/nginx.pid

# Switch to non-root user
USER nginx-user

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
