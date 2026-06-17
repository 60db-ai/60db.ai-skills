# API basics — auth, errors, limits, languages, SDKs, pricing

Hosts: REST `https://api.60db.ai` · WS `wss://api.60db.ai/ws/*` · Docs `https://docs.60db.ai` · Dashboard `https://app.60db.ai`.

## Authentication

- **REST:** header `Authorization: Bearer <key>`. Keys look like `sk_live_…`.
- **WebSocket:** query param `?apiKey=<key>` (or `?token=<jwt>&workspace_id=…`).
- **Get a key:** `app.60db.ai` → Settings → Developer → API Keys → Create API Key.
- **Rotate:** create a new key, swap it into your config/secret, delete the old one. Rotate immediately if a key ever appears in chat, a log, or a commit.

> Keep the key secret: never commit it, never put it in client-side code, never paste it into a chat. This skill stores it at `${XDG_CONFIG_HOME:-~/.config}/60db/config.json` (mode 600) or reads env `SIXTYDB_API_KEY` — never from argv.

## Error / status codes

| Code | Meaning | Fix |
|------|---------|-----|
| 200 / 201 | OK / Created | — |
| 202 | Accepted (async queue) | poll/await the result |
| 400 | Bad request | fix body/params |
| 401 | Unauthorized | check the Bearer key |
| 402 | Insufficient credits | top up the workspace wallet |
| 403 | Forbidden | key lacks scope/permission |
| 404 | Not found | check path / resource id |
| 413 | Payload too large | text ≤ 5000 chars; audio ≤ 10 MB |
| 422 | Unprocessable | fix invalid field values |
| 429 | Too many requests | back off; honor `X-RateLimit-Reset` |
| 500 / 503 | Server error / unavailable | retry with backoff |

WebSocket errors arrive as `{"error":{"context_id":"…","message":"…"}}`.

## Rate limits

Plan-dependent; no fixed numbers published. Every REST response carries `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` (Unix). No documented concurrency cap.

## Supported languages

- **TTS — 30 languages.** `GET /tts/languages`; filter voices / set cloning language by code (`en`, `hi`, …). Includes English + many Indic languages (Assamese, Bengali, Gujarati, Kannada, Malayalam, Marathi, Nepali, Odia, …) plus Russian, Indonesian, Thai, Filipino, Ukrainian, and more.
- **STT — 39 languages** (+ `auto`). `GET /stt/languages`.

```bash
python3 scripts/sixtydb.py langs          # TTS languages
python3 scripts/sixtydb.py langs --stt    # STT languages
```

> Code format is inconsistent in the docs — the languages endpoints return short codes (`en`), while SDK examples show locale codes (`en-us`). Prefer the short codes the endpoint returns.

## Pricing / credits

Pay-as-you-go, debited from a **workspace wallet**. An empty wallet returns `402 Insufficient credits`. The WS `connection_established` frame reports live `credit_balance`; the STT WS `session_stopped` frame reports `billing_summary.total_cost`. No per-character / per-second list price is published in the docs — check `app.60db.ai` and the billing endpoints (`/billing/transactions`, `/billing/usage-logs`, `/analytics/get-usage`).

## Official SDKs (⚠️ verify on the registry before relying on them)

- **JS/TS:** `npm install 60db` → `import { SixtyDBClient } from "60db"`.
- **Python:** `pip install 60db` → `from sixtydb import SixtyDBClient`.
- **MCP server + CLI** also documented under `docs.60db.ai`.

The package name `60db` (leading digit) and the mismatch between package name and import names look like doc placeholders — confirm on npm/PyPI first. **This skill deliberately depends on none of them** — `scripts/sixtydb.py` is stdlib-only, so it keeps working regardless.
