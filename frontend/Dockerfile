# syntax=docker/dockerfile:1
# Build context is the repository root:  docker build -f frontend/Dockerfile .
FROM node:24-alpine AS build
# corepack installs the pnpm version pinned by "packageManager" in the root package.json (the
# same one CI uses). Unpinned, it would fetch the newest major, whose default supply-chain policy
# rejects packages published in the last day and fails `--frozen-lockfile` installs.
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json frontend/
RUN pnpm install --frozen-lockfile --filter ./frontend...
COPY frontend frontend
# No API key is baked into the bundle: nginx injects X-API-Key at runtime (see nginx.conf)
RUN pnpm --dir frontend run build

FROM nginxinc/nginx-unprivileged:1.27-alpine
# The official image renders /etc/nginx/templates/*.template with envsubst into conf.d at start-up
COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
# Must be defined (even empty) or envsubst leaves the literal placeholder in the config
ENV API_ACCESS_KEY=""
COPY frontend/nginx-security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --from=build /repo/frontend/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
