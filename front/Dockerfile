# Stage 1: build front-end bundles with Vite
FROM node:22-slim AS web-build

WORKDIR /front
COPY ./web/ /front/web/
COPY ./src/static/netfront/ /front/src/static/netfront/
COPY ./src/static/config_forms/ /front/src/static/config_forms/

WORKDIR /front/web
RUN npm install --no-audit --no-fund --prefer-offline
RUN npm run build

# Stage 2: python app
FROM python:3.11

WORKDIR /app
RUN pip install setuptools --upgrade
RUN pip install wheel uwsgi
ADD ./requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt
RUN mkdir -p /app/.postgresql && \
    wget "https://storage.yandexcloud.net/cloud-certs/CA.pem" -O /app/.postgresql/root.crt && \
    chmod 0600 /app/.postgresql/root.crt

ADD ./src /app

# Copy built bundles from the node stage
COPY --from=web-build /front/src/static/dist/ /app/static/dist/

ADD run_app.sh /app/run_app.sh
RUN chmod +x /app/run_app.sh

CMD ["/app/run_app.sh"]
