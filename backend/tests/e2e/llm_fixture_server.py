from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SOURCE_CODE = """# secure-engine-e2e-v2
def analyze(payload):
    candles = payload["context"]["candles"]
    return {"signals": [{"action": "HOLD", "phase": "EVALUATED"} for _ in candles]}
"""


def candidate(name: str, display_name: str, rule: str) -> dict[str, object]:
    return {
        "normalizedName": name,
        "displayName": display_name,
        "description": "Deterministic end-to-end generated strategy fixture.",
        "structuredRules": {
            "entry": rule,
            "exit": "Return HOLD when the entry condition is absent.",
            "timing": "Closed candles only.",
        },
        "parameters": [],
        "relationships": [],
        "assumptions": ["Analytical fixture; it never places trades."],
        "evidence": [
            {
                "ruleId": "entry",
                "sourceExcerpt": rule,
                "sourceLocation": "submitted-source",
                "inferred": False,
            }
        ],
        "sourceCode": SOURCE_CODE,
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_error(404)
            return
        self._json(200, {"status": "UP"})

    def do_POST(self) -> None:
        if self.path != "/generate":
            self.send_error(404)
            return
        size = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(size))
        source = payload["input"][1]["content"]
        candidates = (
            [
                candidate(
                    "fixture-breakout",
                    "Fixture Breakout",
                    "BUY on a closed-candle breakout.",
                ),
                candidate(
                    "fixture-reversion",
                    "Fixture Reversion",
                    "BUY on a closed-candle reversion.",
                ),
            ]
            if "MULTI_STRATEGY_FIXTURE" in source
            else [
                candidate(
                    "donchian-breakout",
                    "Donchian Breakout",
                    "BUY when close exceeds the prior bounded channel high.",
                )
            ]
        )
        self._json(200, {"output": {"candidates": candidates}})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status: int, value: object) -> None:
        encoded = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8081), Handler).serve_forever()
