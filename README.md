# YT-DLP Subtitle Downloader Daemon

A simple Flask-based daemon that uses `yt-dlp` to download subtitles (manual and auto-generated) from YouTube URLs without downloading the video itself.

## Features
- Extracts English subtitles (`en.*`) in SRT format.
- Supports both manual and auto-generated subs.
- Timeout protection (5 minutes per request).
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

Send a POST request to `/process` with the raw body containing the URL (first line is used):

