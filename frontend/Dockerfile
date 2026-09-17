ARG NODE_BASE_IMAGE=node:22-alpine
FROM ${NODE_BASE_IMAGE}

ARG NPM_REGISTRY=https://registry.npmjs.org/
ARG PNPM_VERSION=10.33.0

WORKDIR /app

RUN npm install -g "pnpm@${PNPM_VERSION}" --registry "${NPM_REGISTRY}"

COPY package.json ./
RUN pnpm config set registry "${NPM_REGISTRY}" \
  && pnpm install --no-frozen-lockfile

COPY index.html tsconfig.json tsconfig.app.json tsconfig.node.json vite.config.ts ./
COPY public ./public
COPY src ./src

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0", "--port", "5173"]
