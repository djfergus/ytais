import os
import sys
import subprocess
import socketserver

class URLHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            data = self.request.recv(1024).decode('utf-8').strip()
            url = data.split('\n')[0]  # Take first line as URL
            if not url:
                self.request.sendall(b"ERROR: No URL provided\n")
                self.request.close()
                return

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
                response = f"OK\n{result.stdout}\n"
            else:
                response = f"ERROR\n{result.stderr}\n"

            self.request.sendall(response.encode('utf-8'))
        except Exception as e:
            print(f"Handler error: {e}", file=sys.stderr)
            self.request.sendall(f"ERROR: {str(e)}\n".encode('utf-8'))
        finally:
            self.request.close()

if __name__ == "__main__":
    print("Daemon started, listening on TCP port 33032", file=sys.stderr)
    server = socketserver.ThreadingTCPServer(("0.0.0.0", 33032), URLHandler)
    server.timeout = 0.5  # Non-blocking poll
    server.serve_forever()
