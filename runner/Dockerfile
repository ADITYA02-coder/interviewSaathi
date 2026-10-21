# Locked-down code runner. Build:  docker build -t interviewsaathi-runner ./runner
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends nodejs default-jdk-headless && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
ENV RUNNER_CONFIRM_ISOLATED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 9000
# Runs as root ONLY so it can drop user code to `nobody`; capabilities are stripped in docker-compose.yml.
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-9000}"]
