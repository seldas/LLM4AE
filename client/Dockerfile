# -----------------------------------
# Stage 1: Build the app
# -----------------------------------
FROM node:22 AS builder

WORKDIR /app

ENV NODE_ENV=development
ENV NPM_CONFIG_PRODUCTION=false

COPY package.json ./
COPY package-lock.json ./

RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build

# -----------------------------------
# Stage 2: Run the production server
# -----------------------------------
FROM node:22 AS runner

WORKDIR /app

COPY --from=builder /app/.next .next
COPY --from=builder /app/public public
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules node_modules

ENV NODE_ENV=production
EXPOSE 3000

CMD ["npm", "start"]