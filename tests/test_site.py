from __future__ import annotations

import tempfile
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


class SiteTests(unittest.TestCase):
    def test_static_site_contract_and_copy(self) -> None:
        html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "site" / "styles.css").read_text(encoding="utf-8")
        javascript = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
        for forbidden in ("—", "–"):
            self.assertNotIn(forbidden, html)
        self.assertIn('id="lab-canvas"', html)
        self.assertIn('id="reduce-motion"', html)
        self.assertIn('id="asset-error"', html)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("prefers-color-scheme", css)
        self.assertIn(".control-block[hidden]", css)
        self.assertIn("display: none !important;", css)
        self.assertNotIn("h-screen", css)
        self.assertNotIn("window.addEventListener(\"scroll\"", javascript)
        self.assertIn("atlas.naturalWidth !== 1536", javascript)
        self.assertIn("atlas.naturalHeight !== 2288", javascript)
        self.assertIn('atlas.src = "spritesheet.webp"', javascript)
        self.assertIn('reducedAtlas.src = "assets/momo-reduced.webp"', javascript)
        self.assertNotIn("if (effectiveReducedMotion()) activeFrame = 0;", javascript)
        self.assertIn("preserves all sixteen look cells", javascript)
        self.assertIn("\nresetState();\n\natlas.src", javascript)

    def test_site_files_serve_without_a_framework(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            staging = Path(temporary)
            for name in ("index.html", "styles.css", "app.js"):
                (staging / name).write_bytes((ROOT / "site" / name).read_bytes())

            handler = lambda *args, **kwargs: QuietHandler(  # noqa: E731
                *args,
                directory=str(staging),
                **kwargs,
            )
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=5) as response:
                    body = response.read().decode("utf-8")
                    self.assertEqual(response.status, 200)
                    self.assertIn("<title>Momo Ayase", body)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()


if __name__ == "__main__":
    unittest.main()
