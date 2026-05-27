FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn pyjwt httpx
COPY . .
CMD ["python", "scheduler.py"]
