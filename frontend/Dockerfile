# syntax=docker/dockerfile:1
# Build context is the repository root:  docker build -f frontend/Dockerfile .
FROM node:20-alpine AS build
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json frontend/
RUN pnpm install --frozen-lockfile --filter ./frontend...
COPY frontend frontend
# Optional shared secret baked into the bundle (see docs/SETUP_AND_CONFIG.md)
ARG VITE_API_ACCESS_KEY=""
ENV VITE_API_ACCESS_KEY=$VITE_API_ACCESS_KEY
RUN pnpm --dir frontend run build

FROM nginxinc/nginx-unprivileged:1.31-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/frontend/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
