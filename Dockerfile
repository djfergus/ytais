FROM alpine:3.20

RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-cffi \
    ffmpeg \
    git \
    ca-certificates \
    shadow \
    yt-dlp \
    && pip install --break-system-packages --no-cache-dir --upgrade pip \
    && pip install --break-system-packages --no-cache-dir curl-cffi flask \
    && addgroup -g 1000 -S appgroup \
    && adduser -S appuser -u 1000 -G appgroup

USER appuser
WORKDIR /workspace

CMD ["python3", "daemon.py"]
