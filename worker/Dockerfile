# worker/Dockerfile
FROM python:3.10

WORKDIR /app

RUN apt-get update && apt-get install --no-install-recommends -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY worker.py .

CMD ["python", "worker.py"]