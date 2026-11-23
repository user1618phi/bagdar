"""Vercel entry point: the same request handler as `python -m meje`, run as a serverless function.

Vercel hands the function the rewritten path (/api/index), so vercel.json passes the path the
visitor asked for in a query parameter and it is restored here before the normal routing.
"""

import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from meje.server import Handler, build_tutor


class handler(Handler):
    tutor = build_tutor()

    def _restore_path(self) -> None:
        requested = parse_qs(urlsplit(self.path).query).get("__path")
        if requested:
            self.path = requested[0]

    def do_GET(self) -> None:
        self._restore_path()
        super().do_GET()

    def do_POST(self) -> None:
        self._restore_path()
        super().do_POST()
