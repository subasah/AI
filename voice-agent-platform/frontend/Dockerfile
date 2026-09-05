# Optional standalone frontend image (static files only).
# Production compose builds the UI inside nginx/Dockerfile instead.
FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

ARG VITE_API_BASE=
ARG VITE_ADMIN_TOKEN=dev-admin-token
ARG VITE_BASE_PATH=/
ENV VITE_API_BASE=$VITE_API_BASE \
    VITE_ADMIN_TOKEN=$VITE_ADMIN_TOKEN \
    VITE_BASE_PATH=$VITE_BASE_PATH

RUN npm run build && cp dist/index.html dist/404.html

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
