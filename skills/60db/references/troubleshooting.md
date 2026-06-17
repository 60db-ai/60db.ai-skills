# Troubleshooting — the mistakes this skill exists to prevent

Every item below is a real trap discovered the hard way. Check here first.

## "The voice sounds compressed / muffled / not HD"

Not a bitrate or sample-rate bug. The model is ~16 kHz-native and **band-limited to ~8 kHz**. A 48 kHz WAV is upsampled headroom, not real treble. **`enhance` and `60db-quality` do not raise this ceiling.** If you genuinely need full-band (≥ 44.1 kHz with real high frequencies), use a different provider — no 60db knob fixes it. Don't burn renders A/B-ing rates hoping for more treble; verify with a spectrogram once and move on.

## `json.decoder.JSONDecodeError: Extra data`

You parsed the REST `/tts-synthesize` response as one JSON object. **It's NDJSON** — one JSON object per line. Split on newlines, parse each line, concatenate `result.audioContent` (base64 LINEAR16). The engine handles this; if you call the API directly, don't `json.loads(whole_body)`.

## `Unsupported sample_rate_hertz: 44100`

60db (Inworld backend) accepts **8000 / 16000 / 24000 / 48000 only**. Use 48000 for high-fi VO. 44100 is the CD rate but it is rejected here.

## My `--voice` / `--sample-rate` / `--model` is silently ignored

Config resolution is strict: **CLI flag > env `SIXTYDB_*` > config file > built-in default.** A classic bug (now fixed in this engine) was evaluating argparse `default=os.environ.get(...)` *before* the config loaded, so a truthy built-in default short-circuited the real value and you'd silently get the wrong voice/rate. If you fork the engine, keep CLI defaults `None` and resolve **after** loading config. Run `doctor` to see what's actually in effect.

## `output_format` did nothing

`/tts-synthesize` ignores `output_format` and always returns raw PCM. The engine wraps it as WAV. Want MP3/OGG? Transcode the WAV afterward (e.g. ffmpeg).

## `ERROR: no 60db API key found`

No key in env or config. Run `python3 scripts/sixtydb.py init` (hidden prompt) or `export SIXTYDB_API_KEY=sk_live_…`. Never pass the key as a CLI argument — the engine refuses to read it from argv (it would leak into shell history / process lists).

## `HTTP 401` / `HTTP 402`

- **401** — key is wrong, expired, or revoked. Re-run `init` with a fresh key from `app.60db.ai`.
- **402** — workspace wallet is out of credits. Top up at `app.60db.ai`.

## TTS request rejected — text too long

`/tts-synthesize` caps at **5000 characters**. Split the script into chunks, synth each, and concatenate the WAVs (or use the WS stream for very long copy).

## A key got pasted into chat

Treat it as compromised the moment it appears in a message — chat history and platform servers retain it. **Rotate immediately:** create a new key at `app.60db.ai`, delete the old one, and have the user enter the fresh key locally via `init`. Do not reuse the pasted key.

## "The docs say X but it doesn't work"

The published 60db docs are partly inaccurate: the OpenAPI spec is a placeholder ("Plant Store"), the TTS response schema is wrong, the voice-clone input method contradicts itself (multipart files vs `sample_url`), and the `integration/livekit` page 404s. **Trust this skill's verified anchors** (`GET /voices`, the NDJSON TTS response, the allowed sample rates); treat doc-only endpoints (`clone`, `update`/`delete` voice, the alt voice-list paths) as unverified and confirm with a live call before depending on them.

## Quick self-check

```bash
python3 scripts/sixtydb.py doctor          # key present? defaults? websockets?
python3 scripts/sixtydb.py voices | head    # a real list = the key works end-to-end
```
