FROM mcr.microsoft.com/devcontainers/typescript-node:22 AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


FROM mcr.microsoft.com/devcontainers/base:dev-alpine3.21

RUN apk add --no-cache nginx \
  && mkdir -p /usr/share/nginx/html

COPY nginx.conf /etc/nginx/http.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
