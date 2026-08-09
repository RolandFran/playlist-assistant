FROM ghcr.io/home-assistant/base:3.20

WORKDIR /app
# Build with the repository root as context, for example:
# docker build -f ha_app/Dockerfile .
COPY requirements.txt /tmp/requirements.txt
RUN apk add --no-cache python3 py3-pip \
    && pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt
COPY . ./

CMD ["/app/ha_app/run.sh"]
