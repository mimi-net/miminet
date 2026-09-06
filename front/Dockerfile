ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}

WORKDIR /app
RUN pip install setuptools --upgrade
RUN pip install wheel uwsgi uv
COPY pyproject.toml uv.lock /app/
COPY back/pyproject.toml /app/back/pyproject.toml
COPY front/pyproject.toml /app/front/pyproject.toml
RUN uv sync --frozen --no-dev --project front
ENV PATH="/app/.venv/bin:$PATH"
RUN mkdir -p /app/.postgresql && \
    wget "https://storage.yandexcloud.net/cloud-certs/CA.pem" -O /app/.postgresql/root.crt && \
    chmod 0600 /app/.postgresql/root.crt

COPY front/src /app

COPY front/run_app.sh /app/run_app.sh
RUN chmod +x /app/run_app.sh

CMD ["/app/run_app.sh"]
