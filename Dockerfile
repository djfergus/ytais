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
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir curl-cffi \
    && addgroup -g 1000 -S appgroup \
    && adduser -S appuser -u 1000 -G appgroup

USER appuser
WORKDIR /workspace

CMD ["/bin/sh"]
