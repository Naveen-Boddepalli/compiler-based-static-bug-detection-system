"""HTTP server providing REST API and serving the interactive web workbench."""

import http.server
import json
import os
import sys
from typing import Dict, Any

from static_analyzer.pipeline import AnalyzerPipeline

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")

PIPELINE = AnalyzerPipeline()


def load_samples() -> Dict[str, str]:
    """Reads all sample C programs from the samples directory."""
    samples = {}
    if os.path.isdir(SAMPLES_DIR):
        for name in sorted(os.listdir(SAMPLES_DIR)):
            if name.endswith(".c"):
                path = os.path.join(SAMPLES_DIR, name)
                with open(path, "r", encoding="utf-8") as f:
                    samples[name] = f.read()
    return samples


class StaticAnalyzerHandler(http.server.BaseHTTPRequestHandler):
    """Custom request handler for API endpoints and static frontend assets."""

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/api/health":
            self._send_json(200, {
                "status": "healthy",
                "system": "Compiler-Based Static Code Analysis System",
                "language": "C-Subset",
                "passes": ["Lexer", "Parser", "AST", "Semantic Analysis", "CFG", "Data Flow", "Safety Detectors"]
            })
            return

        if path == "/api/samples":
            samples = load_samples()
            self._send_json(200, {"samples": samples})
            return

        # Serve static frontend files
        rel_path = path.lstrip("/")
        if not rel_path or rel_path == "index.html":
            file_path = os.path.join(WEB_DIR, "index.html")
        else:
            clean_rel = os.path.normpath(rel_path).lstrip(os.sep)
            file_path = os.path.join(WEB_DIR, clean_rel)

        if not os.path.isfile(file_path):
            self._send_json(404, {"error": f"Resource not found: {path}"})
            return

        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".zip": "application/zip",
            ".svg": "image/svg+xml",
            ".txt": "text/plain; charset=utf-8",
            ".c": "text/plain; charset=utf-8"
        }
        content_type = mime_map.get(ext, "application/octet-stream")

        if os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        else:
            self._send_json(404, {"error": "Asset not found"})

    def do_POST(self):
        if self.path == "/api/analyze":
            content_len = int(self.headers.get("Content-Length", 0))
            if content_len == 0:
                self._send_json(400, {"error": "Empty request body"})
                return

            body = self.rfile.read(content_len).decode("utf-8")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON body"})
                return

            code = data.get("code", "")
            filename = data.get("filename", "input.c")

            try:
                result = PIPELINE.analyze(code, filename=filename)
                self._send_json(200, result.to_dict())
            except Exception as e:
                self._send_json(500, {
                    "error": f"Internal analyzer error: {str(e)}"
                })
        else:
            self._send_json(404, {"error": f"Endpoint not found: {self.path}"})

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        # Override to suppress default access log clutter while preserving clean output
        pass


def run_server(port: int = 8000, host: str = "127.0.0.1", max_attempts: int = 5):
    http.server.HTTPServer.allow_reuse_address = True
    current_port = port

    httpd = None
    for attempt in range(max_attempts):
        try:
            server_address = (host, current_port)
            httpd = http.server.HTTPServer(server_address, StaticAnalyzerHandler)
            break
        except OSError as e:
            if attempt < max_attempts - 1:
                print(f"Port {current_port} is in use, attempting port {current_port + 1}...")
                current_port += 1
            else:
                print(f"Error: Could not bind to port {current_port}: {e}")
                sys.exit(1)

    print(f"Static Analysis Workbench running at http://{host}:{current_port}/")
    print("Press Ctrl+C to terminate server.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port=port)
