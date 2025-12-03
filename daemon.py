import sys
import subprocess
import re
import time
import glob
import os
from collections import defaultdict
from urllib.parse import urlparse
from flask import Flask, request, jsonify, abort
from openai import OpenAI

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # Fallback if python-dotenv is not available
    pass

app = Flask(__name__)

# Configuration from environment variables
PORT = int(os.environ.get("PORT", 33032))
TIMEOUT = int(os.environ.get("TIMEOUT", 300))
MAX_REQUESTS_PER_MINUTE = int(os.environ.get("MAX_REQUESTS_PER_MINUTE", 5))

# OpenRouter configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
SUMMARY_MODEL = os.environ.get("SUMMARY_MODEL", "x-ai/grok-4.1-fast:free")
ENABLE_SUMMARY = os.environ.get("ENABLE_SUMMARY", "true").lower() == "true"
SUMMARY_TIMEOUT = int(os.environ.get("SUMMARY_TIMEOUT", 120))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", 3))
RETRY_DELAY = int(os.environ.get("RETRY_DELAY", 2))

# Simple rate limiting
request_counts = defaultdict(list)

# Setup logging
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def is_valid_youtube_url(url):
    """Validate YouTube URL format"""
    try:
        result = urlparse(url)
        return result.scheme in ("http", "https") and (
            "youtube.com" in result.netloc or "youtu.be" in result.netloc
        )
    except Exception:
        return False


def is_rate_limited(ip):
    """Check if IP is rate limited"""
    now = time.time()
    request_counts[ip] = [
        t for t in request_counts[ip] if now - t < 60
    ]  # Keep last 60s
    if (
        len(request_counts[ip]) >= MAX_REQUESTS_PER_MINUTE
    ):  # Max requests per minute per IP
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


def generate_summary(subtitle_content, model_override=None):
    """
    Generate summary using OpenRouter API with retry logic
    Returns: (success: bool, summary_data: dict, error: str)
    """
    if not OPENROUTER_API_KEY:
        return False, None, "OpenRouter API key not configured"

    if not ENABLE_SUMMARY:
        return False, None, "Summary generation is disabled"

    model = model_override or SUMMARY_MODEL

    # Initialize OpenAI client for OpenRouter
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        timeout=SUMMARY_TIMEOUT,
    )

    # Prepare the prompt for summary generation
    prompt = f"""Please analyze this subtitle content and provide a summary in the following format:

1. A brief overview (2-3 sentences)
2. Detailed bullet points including:
   - Key topics and themes
   - Countries mentioned
   - Cities mentioned  
   - People mentioned
   - Brands mentioned

Subtitle content:
{subtitle_content}

Provide the summary in a clear, structured format."""

    messages = [
        {
            "role": "system",
            "content": "You are an expert at analyzing video subtitle content and creating comprehensive summaries.",
        },
        {"role": "user", "content": prompt},
    ]

    # Retry logic with exponential backoff
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(
                f"Generating summary with model {model}, attempt {attempt + 1}/{MAX_RETRIES}"
            )

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=None,  # Let model use context limit
                temperature=0.3,
            )

            summary_content = response.choices[0].message.content.strip()

            summary_data = {
                "content": summary_content,
                "model_used": model,
                "retry_attempts": attempt,
            }

            logger.info(f"Summary generated successfully using {model}")
            return True, summary_data, None

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Summary attempt {attempt + 1} failed: {error_msg}")

            if attempt == MAX_RETRIES - 1:
                logger.error(
                    f"Summary generation failed after {MAX_RETRIES} attempts: {error_msg}"
                )
                return False, None, f"Failed after {MAX_RETRIES} retries: {error_msg}"

            # Exponential backoff
            time.sleep(RETRY_DELAY**attempt)

    return False, None, "Unexpected error in summary generation"


@app.before_request
def limit_request_size():
    """Limit request size to prevent abuse"""
    if request.content_length and request.content_length > 1024:  # 1KB limit
        abort(413, "Request too large")


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": time.time()})


@app.route("/process", methods=["POST"])
def process_url():
    """Process YouTube URL and extract subtitles"""
    start_time = time.time()

    try:
        # Rate limiting
        if is_rate_limited(request.remote_addr):
            logger.warning(f"Rate limit exceeded for IP: {request.remote_addr}")
            return jsonify({"status": "ERROR", "error": "Rate limit exceeded"}), 429

        # Content type validation
        if not request.is_json and request.mimetype != "text/plain":
            return jsonify(
                {
                    "status": "ERROR",
                    "error": "Content-Type must be application/json or text/plain",
                }
            ), 400

        # Extract URL and summary parameters based on content type
        summary_model = None
        disable_summary = False

        if request.is_json:
            try:
                json_data = request.get_json()
                url = json_data.get("url", "") if json_data else ""
                summary_model = json_data.get("summary_model") if json_data else None
                disable_summary = (
                    json_data.get("disable_summary", False) if json_data else False
                )
            except Exception:
                return jsonify({"status": "ERROR", "error": "Invalid JSON format"}), 400
        else:
            data = request.get_data().decode("utf-8").strip()
            lines = data.split("\n")
            url = lines[0]  # Take first line as URL

            # Support additional parameters in text/plain format
            if len(lines) > 1:
                summary_model = lines[1].strip() or None
            if len(lines) > 2:
                disable_summary = lines[2].strip().lower() in ("true", "1", "yes")

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
            "--sub-lang",
            "en.*",
            "--convert-subs",
            "srt",
            "--skip-download",
            url,
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd="/workspace", timeout=TIMEOUT
        )

        if result.returncode == 0:
            subtitle_files = get_subtitle_files()

            # Save files to a persistent location
            saved_files = []
            subtitle_content = ""

            for subtitle_file in subtitle_files:
                try:
                    # Create a unique filename based on timestamp
                    timestamp = int(time.time())
                    new_filename = f"subtitles_{timestamp}_{subtitle_file}"
                    os.rename(subtitle_file, new_filename)
                    saved_files.append(new_filename)
                    logger.info(f"Saved subtitle file: {new_filename}")

                    # Read subtitle content for summary generation
                    try:
                        with open(new_filename, "r", encoding="utf-8") as f:
                            subtitle_content += f.read() + "\n"
                    except Exception as e:
                        logger.warning(
                            f"Failed to read {new_filename} for summary: {e}"
                        )

                except Exception as e:
                    logger.error(f"Failed to save {subtitle_file}: {e}")

            # Generate summary if not disabled and content is available
            summary_data = None
            summary_error = None

            if not disable_summary and subtitle_content.strip() and ENABLE_SUMMARY:
                logger.info("Generating summary for subtitle content")
                success, data, error = generate_summary(subtitle_content, summary_model)

                if success:
                    summary_data = data
                    logger.info(
                        f"Summary generated successfully using {data['model_used']}"
                    )
                else:
                    summary_error = error
                    logger.warning(f"Summary generation failed: {error}")
            elif disable_summary:
                logger.info("Summary generation disabled by request parameter")
            elif not subtitle_content.strip():
                logger.warning("No subtitle content available for summary generation")
            elif not ENABLE_SUMMARY:
                logger.info("Summary generation disabled by configuration")

            # Prepare response based on summary generation result
            response_data = {"subtitle_files": saved_files, "output": result.stdout}

            if summary_data:
                response_data["summary"] = summary_data
                response_data["status"] = "OK"
            elif summary_error:
                response_data["summary_error"] = summary_error
                response_data["status"] = "PARTIAL_SUCCESS"
            else:
                response_data["status"] = "OK"

            duration = time.time() - start_time
            logger.info(
                f"Request completed in {duration:.2f}s with status: {response_data['status']}"
            )

            # Return appropriate HTTP status code
            status_code = 200 if response_data.get("status") == "OK" else 207
            return jsonify(response_data), status_code
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
