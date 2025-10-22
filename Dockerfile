FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11

COPY ./app ./app
COPY ./astrea-shapes.ttl ./astrea-shapes.ttl
COPY ./data ./data

ENV PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8000 \
    TRIPLESTORE_URL=http://fuseki:3030/ds

EXPOSE 8000
CMD ["python", "-m", "app.main"]
