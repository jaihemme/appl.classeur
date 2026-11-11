#!/usr/bin/env python3

import json
import os
import subprocess
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

SWIFTOCR = os.environ.get("SWIFTOCR", "/usr/local/bin/swiftocr")
SWIFTOCR_DIR = Path(os.environ["SWIFTOCR_DIR"]).resolve()
PORT = int(os.environ.get("SWIFTOCR_PORT", "8765"))


class Handler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != "/ocr":
            self.send_error(404)
            return

        try:
            length = int(self.headers["Content-Length"])

            if length > 65536:
                self.send_error(413)
                return

            params = json.loads(self.rfile.read(length))

            filename = params["file"]
            lang = params.get("lang", "fr-FR")
            pages = str(params.get("pages", "1"))

            # Reconstruire le chemin macOS
            path = (SWIFTOCR_DIR / filename).resolve()

            # Empêcher l'accès hors du répertoire autorisé
            if not path.is_relative_to(SWIFTOCR_DIR):
                self.send_error(403)
                return

            if not path.is_file():
                self.send_error(404, "File not found")
                return

            try:
                result = subprocess.run(
                    [SWIFTOCR, str(path), "--lang", lang, "--pages", pages],
                    capture_output=True,
                    text=True
                )
            except Exception as e:
                self.send_error(500, f"{e}")
                return

            response = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

            data = json.dumps(response).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        except (ValueError, KeyError, TypeError) as e:
            self.send_error(400, str(e))


if __name__ == "__main__":
    print(f"SwiftOCR directory: {SWIFTOCR_DIR}")
    print(f"SwiftOCR executable: {SWIFTOCR}")
    print(f"Listening on port {PORT}")

    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
