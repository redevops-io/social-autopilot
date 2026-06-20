# agentic-social-autopilot — FastAPI agent layer + MD3 dashboard over a real Postiz core.
FROM python:3.12-slim

WORKDIR /app

# postgresql-client provides `psql`, used to read/write Postiz's postgres over TCP.
# (In a container we can't `docker exec` into the Postiz postgres, so the agent talks
#  to it over the wire; the container is attached to the Postiz docker network.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Live data config is injected at runtime (compose env):
#   POSTIZ_FRONT_URL, POSTIZ_ORG_ID,
#   POSTIZ_PG_HOST, POSTIZ_PG_PORT, POSTIZ_PG_USER, POSTIZ_PG_DB, POSTIZ_PG_PASSWORD
ENV PORT=8206
EXPOSE 8206

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8206"]
