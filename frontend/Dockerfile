# --- Зависимости (общий слой для dev и сборки) ---
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- Разработка: Vite dev server с hot reload (используется в compose.yaml) ---
FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

# --- Сборка статики. VITE_* вшиваются в бандл на этапе сборки ---
FROM deps AS build
ARG VITE_STT_ENGINE=browser
ARG VITE_USE_MOCKS=false
ENV VITE_STT_ENGINE=$VITE_STT_ENGINE \
    VITE_USE_MOCKS=$VITE_USE_MOCKS
COPY . .
RUN npm run build

# --- Прод: nginx отдаёт статику и проксирует /api на бэкенд ---
FROM nginx:1.27-alpine AS prod
# Адрес бэкенда подставляется в конфиг при старте (envsubst из образа nginx)
ENV API_UPSTREAM=http://backend:8000
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
