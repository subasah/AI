# Build React admin UI, then serve via Nginx (reverse proxy + static)
FROM node:22-alpine AS frontend-build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

ARG VITE_API_BASE=
ARG VITE_ADMIN_TOKEN=dev-admin-token
ARG VITE_BASE_PATH=/
ENV VITE_API_BASE=$VITE_API_BASE \
    VITE_ADMIN_TOKEN=$VITE_ADMIN_TOKEN \
    VITE_BASE_PATH=$VITE_BASE_PATH

RUN npm run build && cp dist/index.html dist/404.html

FROM nginx:1.27-alpine

RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
