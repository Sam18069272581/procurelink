"""
serve.py — local preview server for ProcureLink
Starts a simple HTTP server so index.html can fetch data.json (avoids CORS/file:// issue).

Usage:
    python serve.py

Then open: http://localhost:8000
"""
import http.server
import socketserver
import webbrowser
import threading

PORT = 8000

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress noisy request logs, only show errors
        if args[1] not in ("200", "304"):
            super().log_message(format, *args)

def main():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"\n  ProcureLink running at {url}")
        print("  Press Ctrl+C to stop\n")
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        httpd.serve_forever()

if __name__ == "__main__":
    main()