# The relay as a container: docker build -t claude-watch-relay .
# /data holds the Firebase key (firebase-key.json), which the relay only reads. See README.md.
FROM python:3.12-slim

# PUID and PGID: the user the relay runs as; it must be able to read /data/firebase-key.json.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FCM_KEY_FILE=/data/firebase-key.json \
    PUID=99 \
    PGID=100

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY relay relay

EXPOSE 8000
HEALTHCHECK --interval=1m --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
# Never runs as root
CMD ["sh", "-c", "exec setpriv --reuid=\"$PUID\" --regid=\"$PGID\" --clear-groups uvicorn relay.web:create_app --factory --host 0.0.0.0 --port 8000 --no-server-header"]
