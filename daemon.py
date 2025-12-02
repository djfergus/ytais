import sys
import subprocess
import re
import time
import glob
import os
from collections import defaultdict
from urllib.parse import urlparse
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

# Configuration from environment variables
PORT = int(os.environ.get('PORT', 33032))
TIMEOUT = int(os.environ.get('TIMEOUT', 300))
MAX_REQUESTS_PER_MINUTE = int(os.environ.get('MAX_REQUESTS_PER_MINUTE', 5))

# Simple rate limiting
request_counts = defaultdict(list)

# Setup logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_valid_youtube_url(url):
    """Validate YouTube URL format"""
    try:
        result = urlparse(url)
        return result.scheme in ('http', 'https') and (
            'youtube.com' in result.netloc or 'youtu.be' in result.netloc
        )
    except Exception:
        return False

def is_rate_limited(ip):
    """Check if IP is rate limited"""
    now = time.time()
    request_counts[ip] = [t for t in request_counts[ip] if now - t < 60]  # Keep last 60s
    if len(request_counts[ip]) >= MAX_REQUESTS_PER_MINUTE:  # Max requests per minute per IP
        return True
    request_counts[ip].append(now)
    return False

def cleanup_subtitles():
    """Remove .srt files from workspace"""
    for file in glob.glob("*.srt"):
        try:
            os.remove(file)
        except Exception as e:
            print(f"Failed to remove {file}: {e}", file=sys.stderr)

def get_subtitle_files():
    """Get list of generated subtitle files"""
    return glob.glob("*.srt")

@app.before_request
def limit_request_size():
    """Limit request size to prevent abuse"""
    if request.content_length and request.content_length > 1024:  # 1KB limit
        abort(413, "Request too large")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": time.time()})

@app.route('/process', methods=['POST'])
def process_url():
    """Process YouTube URL and extract subtitles"""
    start_time = time.time()
    
    try:
        # Rate limiting
        if is_rate_limited(request.remote_addr):
            logger.warning(f"Rate limit exceeded for IP: {request.remote_addr}")
            return jsonify({"status": "ERROR", "error": "Rate limit exceeded"}), 429
        
        # Content type validation
        if not request.is_json and request.mimetype != 'text/plain':
            return jsonify({"status": "ERROR", "error": "Content-Type must be application/json or text/plain"}), 400
        
        data = request.get_data().decode('utf-8').strip()
        url = data.split('\n')[0]  # Take first line as URL
        
        if not url:
            return jsonify({"status": "ERROR", "error": "No URL provided"}), 400
        
        if not is_valid_youtube_url(url):
            return jsonify({"status": "ERROR", "error": "Invalid YouTube URL"}), 400
        
        logger.info(f"Processing request from {request.remote_addr}: {url}")
        print(f"Processing URL: {url}", file=sys.stderr)

        cmd = [
            "yt-dlp",
            "--write-subs",
            "--write-auto-subs",
            "--sub-lang", "en.*",
            "--convert-subs", "srt",
            "--skip-download",
            url
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd="/workspace",
            timeout=TIMEOUT
        )

        if result.returncode == 0:
            subtitle_files = get_subtitle_files()
            
            # Save files to a persistent location
            saved_files = []
            for subtitle_file in subtitle_files:
                try:
                    # Create a unique filename based on timestamp
                    timestamp = int(time.time())
                    new_filename = f"subtitles_{timestamp}_{subtitle_file}"
                    os.rename(subtitle_file, new_filename)
                    saved_files.append(new_filename)
                    logger.info(f"Saved subtitle file: {new_filename}")
                except Exception as e:
                    logger.error(f"Failed to save {subtitle_file}: {e}")
            
            duration = time.time() - start_time
            logger.info(f"Request completed successfully in {duration:.2f}s")
            return jsonify({
                "status": "OK", 
                "output": result.stdout,
                "subtitle_files": saved_files
            })
        else:
            # Check for common yt-dlp errors
            if "ERROR: Sign in to confirm your age" in result.stderr:
                error_msg = "Video requires age verification"
            elif "ERROR: This video is unavailable" in result.stderr:
                error_msg = "Video is unavailable"
            else:
                error_msg = result.stderr
            
            duration = time.time() - start_time
            logger.error(f"Request failed in {duration:.2f}s: {error_msg}")
            return jsonify({"status": "ERROR", "error": error_msg}), 500

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        logger.error(f"Request timed out after {duration:.2f}s")
        return jsonify({"status": "ERROR", "error": "Request timed out"}), 408
    except UnicodeDecodeError:
        logger.error("Invalid character encoding in request")
        return jsonify({"status": "ERROR", "error": "Invalid character encoding"}), 400
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Handler error after {duration:.2f}s: {e}")
        print(f"Handler error: {e}", file=sys.stderr)
        return jsonify({"status": "ERROR", "error": "Internal server error"}), 500

if __name__ == "__main__":
    print("Daemon started, listening on HTTP port 33032", file=sys.stderr)
    app.run(host="0.0.0.0", port=PORT, threaded=True)
