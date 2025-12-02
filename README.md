# YT-DLP Subtitle Downloader Daemon

A simple Flask-based daemon that uses `yt-dlp` to download subtitles (manual and auto-generated) from YouTube URLs without downloading the video itself.

## Features
- Extracts English subtitles (`en.*`) in SRT format.
- Supports both manual and auto-generated subs.
- Timeout protection (configurable, default 5 minutes per request).
- Security features: URL validation, rate limiting, request size limits.
- Health check endpoint for monitoring.
- Structured logging for debugging and monitoring.
- Automatic cleanup of generated subtitle files.
- Runs in Docker for easy deployment.

## Quick Start (Local Development)

1. Ensure Docker and Docker Compose are installed.
2. Clone or copy the files to a directory.
3. Run:
   ```
   docker-compose up --build
   ```
4. The service will be available at `http://localhost:33032`.

## API Usage

### Health Check
GET `/health`
Returns service status and timestamp.

### Process URL
POST `/process` with the raw body containing the URL (first line is used):

