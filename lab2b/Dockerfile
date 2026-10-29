FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask requests
COPY . .
RUN mkdir -p /data
CMD ["python", "gateway.py"]
