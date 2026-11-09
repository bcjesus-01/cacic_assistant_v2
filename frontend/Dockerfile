FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# URL pública da API: o Next.js a embute no bundle em tempo de build
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
# Constrói a versão de produção
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
# Sem isso, o servidor standalone pode escutar só no hostname do contêiner
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
# Copia apenas os arquivos estáticos e o servidor otimizado do Next.js
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
