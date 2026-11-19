FROM python:3.12-slim
WORKDIR /app
COPY returnledger/ returnledger/
COPY data/ data/
USER 65534:65534
EXPOSE 8080
CMD ["python", "-m", "returnledger", "serve", "--host", "0.0.0.0"]
