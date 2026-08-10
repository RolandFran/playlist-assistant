FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION
ARG BUILD_ARCH
LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}"

WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN apk add --no-cache python3 py3-pip \
    && pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt
COPY . /app/
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
