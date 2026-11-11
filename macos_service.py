# swift_server.py (sur macOS)

from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/run":
            self.send_error(404)
            return

        result = subprocess.run(
            ["ls", "-la", "-tr"],
            capture_output=True,
            text=True
        )

        data = result.stdout.encode()
        self.send_response(200 if result.returncode == 0 else 500)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

HTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
