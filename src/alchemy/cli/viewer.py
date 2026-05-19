import argparse
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from alchemy.config import load_settings


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Alchemy Viewer</title>
  <style>
    html, body {
      margin: 0;
      width: 100%;
      height: 100%;
      background: #050505;
      overflow: hidden;
      color: #ddd;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main {
      width: 100vw;
      height: 100vh;
      display: grid;
      place-items: center;
      background: #050505;
    }
    img {
      width: 100vw;
      height: 100vh;
      object-fit: contain;
      image-rendering: auto;
    }
    .empty {
      font-size: 14px;
      letter-spacing: 0;
      opacity: 0.72;
    }
    .hud {
      position: fixed;
      left: 12px;
      bottom: 10px;
      padding: 6px 8px;
      background: rgba(0, 0, 0, 0.55);
      color: rgba(255, 255, 255, 0.78);
      font-size: 12px;
      border-radius: 4px;
      user-select: none;
    }
  </style>
</head>
<body>
  <main id="stage"><div class="empty">Waiting for output/current.png</div></main>
  <div class="hud" id="hud">Alchemy Viewer</div>
  <script>
    const stage = document.getElementById("stage");
    const hud = document.getElementById("hud");
    let lastMtime = null;

    async function tick() {
      try {
        const response = await fetch("/status", { cache: "no-store" });
        const status = await response.json();

        if (!status.exists) {
          lastMtime = null;
          stage.innerHTML = '<div class="empty">Waiting for output/current.png</div>';
          hud.textContent = "No image yet";
          return;
        }

        if (status.mtime !== lastMtime) {
          lastMtime = status.mtime;
          const image = new Image();
          image.onload = () => {
            stage.replaceChildren(image);
            hud.textContent = new Date(status.mtime * 1000).toLocaleTimeString();
          };
          image.src = `/current.png?mtime=${encodeURIComponent(status.mtime)}`;
          image.alt = "Current Alchemy output";
        }
      } catch (error) {
        hud.textContent = "Viewer disconnected";
      }
    }

    tick();
    setInterval(tick, 500);
  </script>
</body>
</html>
"""


class ViewerHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, image_path: Path, **kwargs) -> None:
        self.image_path = image_path
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/":
            self._send_html(HTML)
            return

        if route == "/status":
            self._send_json(self._status())
            return

        if route == "/current.png":
            self._send_image()
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_HEAD(self) -> None:
        route = urlparse(self.path).path
        if route == "/current.png" and self.image_path.exists():
            stat = self.image_path.stat()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(stat.st_size))
            self.end_headers()
            return

        if route == "/":
            encoded = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        return

    def _status(self) -> dict[str, object]:
        if not self.image_path.exists():
            return {"exists": False, "path": str(self.image_path)}

        stat = self.image_path.stat()
        return {
            "exists": True,
            "path": str(self.image_path),
            "mtime": stat.st_mtime,
            "size": stat.st_size,
        }

    def _send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, body: dict[str, object]) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_image(self) -> None:
        if not self.image_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        data = self.image_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/png")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def parse_args() -> argparse.Namespace:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Serve a local browser viewer for output/current.png.")
    parser.add_argument("--host", default=settings.alchemy_viewer_host, help="Viewer host.")
    parser.add_argument("--port", type=int, default=settings.alchemy_viewer_port, help="Viewer port.")
    parser.add_argument("--image", type=Path, default=settings.alchemy_current_image, help="Image to watch.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    handler = partial(ViewerHandler, image_path=args.image)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    url = f"http://{args.host}:{args.port}"
    print(f"Alchemy viewer serving {args.image}")
    print(f"Open {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping viewer.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
