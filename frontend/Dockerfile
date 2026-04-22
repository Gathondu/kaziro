# syntax=docker/dockerfile:1.7
# Multi-stage build for the SvelteKit frontend.
#
# In production we deploy via the Vercel adapter, but for local
# docker-compose we just run the Vite dev server (HMR + source maps) so
# that ``frontend/`` mounts behave like a normal dev environment.
#
# Build context is the repository root; the application source lives under
# ``frontend/``. Run with::
#
#     docker build -f frontend/Dockerfile -t kaziro/frontend .

ARG NODE_VERSION=20

# --- base ---------------------------------------------------------------
FROM node:${NODE_VERSION}-bookworm-slim AS base

ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH \
    CI=true

RUN corepack enable && corepack prepare pnpm@10.33.1 --activate

WORKDIR /app

# --- deps ---------------------------------------------------------------
FROM base AS deps

COPY frontend/package.json frontend/pnpm-lock.yaml ./

RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile

# --- build --------------------------------------------------------------
FROM base AS build

COPY --from=deps /app/node_modules ./node_modules
COPY frontend ./

RUN pnpm build

# --- runtime ------------------------------------------------------------
# Local dev image: ships the dev server. Production deploys go to Vercel
# via the SvelteKit adapter and don't use this stage.
FROM base AS dev

ARG APP_USER=kaziro
ARG APP_UID=10001

RUN groupadd --system --gid ${APP_UID} ${APP_USER} \
    && useradd --system --uid ${APP_UID} --gid ${APP_USER} --create-home ${APP_USER}

COPY --from=deps /app/node_modules ./node_modules
COPY frontend ./

RUN chown -R ${APP_USER}:${APP_USER} /app

USER ${APP_USER}

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0", "--port", "5173"]
