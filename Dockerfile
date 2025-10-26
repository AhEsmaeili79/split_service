FROM python:3.11-slim AS base

WORKDIR /split_service

COPY requirements.txt .

COPY --from=curlimages/curl:latest /usr/bin/curl /usr/bin/curl

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
