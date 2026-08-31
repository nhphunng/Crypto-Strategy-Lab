KNOWN_BREAKOUT = {
    "normalized_name": "donchian-breakout",
    "display_name": "Donchian Breakout",
    "description": "Buy above the prior channel high and sell below its low.",
    "structured_rules": {
        "entry": "close > prior_channel_high",
        "exit": "close < prior_channel_low",
    },
    "assumptions": ("Closed candles only",),
    "evidence": ("widely known deterministic definition",),
    "source_code": "def analyze(payload):\n    return {'signals': []}\n",
}

UNKNOWN = ()
AMBIGUOUS = (KNOWN_BREAKOUT, {**KNOWN_BREAKOUT, "normalized_name": "price-breakout"})
