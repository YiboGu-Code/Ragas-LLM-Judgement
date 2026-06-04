FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV APP_SQLITE_PATH=/app/data/app.db
ENV APP_DATASET_DIR=/app/data/datasets
ENV APP_ARTIFACT_DIR=/app/artifacts

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
