---
name: 60db
description: 60db.ai voice platform via one zero-dependency CLI — text-to-speech (TTS), speech-to-text (STT), voice cloning, voice management, supported-language lookup, and LLM chat (the conversational core for voice agents). Use when the user wants 60db.ai narration / voiceover, to synthesize or transcribe audio, clone or list voices, or build a voice agent — or whenever they type /60db or mention 60db, sixtydb, or "60 db".
---

# 60db.ai voice platform

One CLI — `scripts/sixtydb.py` (stdlib only, Python 3.8+) — for every 60db.ai use case. Base host `https://api.60db.ai`.

> **First time here?** Run the `/setup-60db` skill (or read [Setup](#setup)). It collects the API key **privately** and picks your defaults. Do not start synthesizing before setup, or you will hit `no API key found`.

## Setup

Setup is the **user's** job — never type, paste, print, or commit their key. Direct them:

```bash
python3 scripts/sixtydb.py init      # hidden prompt for the key (never echoed) -> config mode 600
```

The key is read from the config file (`${XDG_CONFIG_HOME:-~/.config}/60db/config.json`) or env `SIXTYDB_API_KEY` — **never** from argv. In a chat session the user can't paste a hidden prompt where you are: run `init --no-key` yourself (scaffolds defaults, never touches the key), then ask them to run `init` on their host. If the user pastes a key into chat anyway, **do not use it** — tell them to rotate it at app.60db.ai and enter the fresh one locally. Get a key at `https://app.60db.ai` → Settings → Developer → API Keys.

Verify any time: `python3 scripts/sixtydb.py doctor` (reports key presence without revealing it).

## Ask before you act (AskUserQuestion)

When the request is underspecified, ask in **one round** (use the platform's blocking question tool — `AskUserQuestion` in Claude Code) — only the choices that change output:

| Ask | When | Options |
|-----|------|---------|
| **Use case** | intent unclear | TTS · STT · clone a voice · list voices · chat/agent |
| **Voice** | TTS/clone, none set | run `voices` first, offer real ids by name |
| **Model** | TTS | `60db-quality` (default, best tier) vs base |
| **Sample rate (kHz)** | TTS | 48000 (default) · 24000 · 16000 · 8000 — **never 44100 (rejected)** |
| **Output / format** | TTS/STT | WAV (default) · raw PCM; STT: plain text · JSON with timings |

Skip the questions when the user already specified, said "just do it", or it's obvious. Persist answers as defaults via `init --no-key --voice … --model … --sample-rate …`.

## Quick start by use case

```bash
# TTS — text or a .txt file -> WAV (REST, 48 kHz, 60db-quality, enhance:true)
python3 scripts/sixtydb.py tts "Hello there." --out out/hello.wav
python3 scripts/sixtydb.py tts script.txt --voice <id> --out out/vo.wav

# STT — audio -> transcript (auto-detects language; --diarize, --timestamps, --json)
python3 scripts/sixtydb.py stt recording.mp3 --diarize --timestamps

# Voices — list ids (built-in + your cloned), then pick one
python3 scripts/sixtydb.py voices
python3 scripts/sixtydb.py langs            # supported languages (--stt for STT's 39)

# Voice cloning (UNVERIFIED endpoint — test first; see references/voices.md)
python3 scripts/sixtydb.py clone --name "My Voice" --sample a.wav --sample b.wav

# Chat — the LLM core you pair with stt+tts for a voice agent (no native calling API)
python3 scripts/sixtydb.py chat "Summarize attachment theory in one line."
```

Config resolution everywhere: **CLI flag > env `SIXTYDB_*` > config file > built-in default.**

## Route the request

| The user wants | Command | Read first |
|----------------|---------|-----------|
| Narration / voiceover / TTS | `tts` | [references/tts.md](references/tts.md) |
| Transcription / subtitles / STT | `stt` | [references/stt.md](references/stt.md) |
| Clone / manage / list voices | `voices` · `clone` · `delete-voice` | [references/voices.md](references/voices.md) |
| Voice agent / calling / "phone bot" | `chat` (+ stt + tts) | [references/agents-calling.md](references/agents-calling.md) |
| Languages, errors, limits, SDKs, pricing | `langs` | [references/api.md](references/api.md) |
| It broke / sounds wrong / "compressed" | `doctor` | [references/troubleshooting.md](references/troubleshooting.md) |

## Gotchas that bite everyone (full list: references/troubleshooting.md)

- **Sample rate ≠ fidelity.** The model is ~16 kHz-native and band-limited to ~8 kHz; 48 kHz output is upsampled headroom, so the voice can sound a touch "compressed". `enhance` and `60db-quality` do **not** raise the ceiling — a swap to a full-band provider does.
- **REST `/tts-synthesize` returns NDJSON**, not one JSON blob: concatenate each line's `result.audioContent` (base64 LINEAR16). It returns **no** sample-rate metadata and ignores `output_format` (always raw PCM → wrap as WAV).
- **Allowed sample rates: 8000 / 16000 / 24000 / 48000 only.** 44100 is rejected.
- **TTS text caps at 5000 chars** per request — split longer scripts and concatenate WAVs.
- **The published docs are partly inaccurate** (placeholder OpenAPI; wrong TTS response schema; voice-clone input method contradicts itself). Trust this skill's verified anchors; flag the rest.

## Security

The API key never transits chat and is never committed. `.gitignore` excludes the config and `out/`. Only the user-run `init` writes the key. See [references/api.md](references/api.md) for auth + key rotation.
