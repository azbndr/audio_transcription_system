# api/Dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install --no-install-recommends -y \
    curl

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]