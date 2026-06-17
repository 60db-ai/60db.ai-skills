# TTS — text-to-speech

Three transports. **Prefer REST `/tts-synthesize` (the CLI default)** — simplest, highest fidelity, one request.

| Transport | Endpoint | When |
|-----------|----------|------|
| REST one-shot | `POST https://api.60db.ai/tts-synthesize` | default — whole script in one call |
| REST stream | `POST https://api.60db.ai/tts-stream` | progressive playback (NDJSON chunks) |
| WebSocket | `wss://api.60db.ai/ws/tts?apiKey=<key>` | realtime, sentence-by-sentence (`--ws`; band-limited) |

## REST `/tts-synthesize` (verified)

Headers: `Authorization: Bearer <key>`, `Content-Type: application/json`.

Request body:

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `text` | string | — | **≤ 5000 chars**. Over that → split + concatenate WAVs. |
| `voice_id` | string | — | from `GET /voices` (the `id` field) |
| `model` | string | — | `60db-quality` = highest tier (honored here) |
| `enhance` | bool | `true` | post-processing; does **not** raise the bandwidth ceiling |
| `speed` | number | `1.0` | 0.5–2.0 |
| `stability` | int | `50` | 0–100 |
| `similarity` | int | `75` | 0–100 |
| `output_format` | string | — | **ignored** by this endpoint — output is always raw PCM |

**Response is line-delimited JSON (NDJSON), not a single object.** Each non-empty line:

```json
{"result":{"audioContent":"<base64 LINEAR16 PCM>"}}
```

Decode and concatenate every line's `result.audioContent`, then wrap the PCM as a mono 16-bit WAV. The endpoint returns **no** sample-rate metadata — write the WAV at the rate you intend (REST native = **48000 Hz**). The engine does all of this.

> ⚠️ The published `text-to-speech` doc page shows a different single-JSON shape (`{audio_base64, sample_rate, duration_seconds, output_format}`). That schema is inaccurate in practice — the NDJSON `result.audioContent` shape above is what the live API returns.

## Sample rates

Allowed: **8000 / 16000 / 24000 / 48000 Hz only. 44100 is rejected** ("Unsupported sample_rate_hertz"). 48 kHz is the high-fi choice for VO. Encoding constraints on WS: `LINEAR16`/`PCM` → all four rates; `MULAW`/`ULAW` → 8000 only; `OGG_OPUS` → 24000 only.

## Fidelity ceiling (read before promising "HD voice")

The model is ~16 kHz-native and **band-limited to ~8 kHz**. A 48 kHz WAV is upsampled headroom, not real treble — so the voice can sound slightly "compressed". Neither `enhance` nor `60db-quality` lifts this ceiling; only a different, full-band provider does. Set expectations accordingly.

## WebSocket (`--ws`, legacy)

`wss://api.60db.ai/ws/tts?apiKey=<key>` (auth is a query param here — the one exception). Frame flow:

```
create_context {context_id, voice_id, audio_config:{audio_encoding:LINEAR16, sample_rate_hertz}}
send_text     {context_id, text}        # one per line/sentence
flush_context {context_id}              # triggers synthesis
  <- audio_chunk {context_id, audioContent}   # base64, repeated
  <- flush_completed {context_id}
close_context {context_id}
```

Server greets with `connection_established` (carries live `credit_balance`); wait for it, then `context_created`, before sending text. Needs the optional `websockets` pip package. Same ~8 kHz ceiling.

## CLI

```bash
python3 scripts/sixtydb.py tts "Hello." --out out/hello.wav
python3 scripts/sixtydb.py tts script.txt --voice <id> --model 60db-quality --sample-rate 48000
python3 scripts/sixtydb.py tts script.txt --speed 0.95 --stability 60 --no-enhance
python3 scripts/sixtydb.py tts script.txt --ws --sample-rate 24000      # legacy stream
```
