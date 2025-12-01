import sys
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process_url():
    try:
        data = request.get_data().decode('utf-8').strip()
        url = data.split('\n')[0]  # Take first line as URL
        if not url:
            return jsonify({"status": "ERROR", "error": "No URL provided"}), 400

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
            timeout=300  # 5 min timeout per request
        )

        if result.returncode == 0:
            return jsonify({"status": "OK", "output": result.stdout})
        else:
            return jsonify({"status": "ERROR", "error": result.stderr}), 500

    except subprocess.TimeoutExpired:
        return jsonify({"status": "ERROR", "error": "Request timed out"}), 408
    except Exception as e:
        print(f"Handler error: {e}", file=sys.stderr)
        return jsonify({"status": "ERROR", "error": str(e)}), 500

if __name__ == "__main__":
    print("Daemon started, listening on HTTP port 33032", file=sys.stderr)
    app.run(host="0.0.0.0", port=33032, threaded=True)
