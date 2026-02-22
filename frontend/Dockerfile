FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json yarn.lock* package-lock.json* ./
RUN npm install --frozen-lockfile || yarn install --frozen-lockfile || npm install
COPY . .
RUN npm run build || yarn build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
