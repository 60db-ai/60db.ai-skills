# 60db Skill — In-Depth Guide

Everything the `/60db` skill can do, with real commands and the output you should expect. The skill fronts one zero-dependency CLI — `skills/60db/scripts/sixtydb.py` (stdlib Python 3.8+) — against `https://api.60db.ai`.

Throughout this guide, `$E` is shorthand for the engine:

```bash
E=skills/60db/scripts/sixtydb.py
```

> Voice ids below (e.g. `fbb75ed2-975a-40c7-9e06-38e30524a9a1`) are placeholders. Run `python3 $E voices` to get the ones on **your** workspace.

---

## Table of contents

1. [Install](#1-install)
2. [Authentication & security](#2-authentication--security)
3. [Config & precedence](#3-config--precedence)
4. [The mental model](#4-the-mental-model-read-this-once)
5. [Commands in depth](#5-commands-in-depth)
6. [Recipes (cookbook)](#6-recipes-cookbook)
7. [Errors & troubleshooting](#7-errors--troubleshooting)
8. [Driving it through the agent](#8-driving-it-through-the-agent)

---

## 1. Install

```bash
# Recommended — installs the 60db + setup-60db skills
npx skills add 60db-ai/60db.ai-skills

# Or clone + run the installer (symlink by default; --copy to copy)
git clone https://github.com/60db-ai/60db.ai-skills.git
cd 60db.ai-skills && ./install.sh
```

Install into another agent's skills dir:

```bash
CLAUDE_SKILLS_DIR=~/.codex/skills ./install.sh             # Codex
CLAUDE_SKILLS_DIR=~/.config/opencode/skills ./install.sh   # OpenCode
```

**Restart your agent session after installing** — skills are only loaded at session start.

Only `python3` 3.8+ is required. The single optional dependency is `websockets`, used solely by the legacy `tts --ws` path:

```bash
python3 -m pip install websockets
```

---

## 2. Authentication & security

The API key is **the user's to enter**. The engine reads it from exactly two places, in this order:

1. Env var `SIXTYDB_API_KEY` (CI-friendly)
2. The local config file `${XDG_CONFIG_HOME:-~/.config}/60db/config.json` (mode `600`)

It is **never** read from the command line, **never** printed, and `.gitignore` keeps the config out of git.

```bash
python3 $E init       # hidden prompt — your keystrokes are not echoed
python3 $E doctor     # confirms the key is present without revealing it
```

Get a key at **app.60db.ai → Settings → Developer → API Keys** (keys look like `sk_live_…`).

**In an agent chat**, the agent can't reach your hidden prompt, so it scaffolds defaults for you:

```bash
python3 $E init --no-key --voice <id> --model 60db-quality   # writes defaults, never touches the key
```

…then you run `python3 $E init` yourself to enter the key. **Never paste a key into chat** — chat history is retained by the platform. If a key leaks, rotate it at app.60db.ai.

For CI / ephemeral environments, set the env var instead of a config file:

```bash
export SIXTYDB_API_KEY=sk_live_xxx
```

---

## 3. Config & precedence

Every setting resolves the same way, most-specific wins:

```
CLI flag  >  env SIXTYDB_<NAME>  >  config file  >  built-in default
```

| Setting | Config key | Env var | Default |
|---------|-----------|---------|---------|
| Voice id | `voice_id` | `SIXTYDB_VOICE_ID` | *(none — required for TTS)* |
| Model | `model` | `SIXTYDB_MODEL` | `60db-quality` |
| Sample rate | `sample_rate` | `SIXTYDB_SAMPLE_RATE` | `48000` |
| Output format | `output_format` | `SIXTYDB_OUTPUT_FORMAT` | `wav` |
| Speed | `speed` | `SIXTYDB_SPEED` | `1.0` |
| Stability | `stability` | `SIXTYDB_STABILITY` | `50` |
| Similarity | `similarity` | `SIXTYDB_SIMILARITY` | `75` |
| Chat model | `chat_model` | `SIXTYDB_CHAT_MODEL` | `60db-tiny` |

Pin project defaults once so you stop repeating flags:

```bash
python3 $E init --no-key --voice fbb75ed2-975a-40c7-9e06-38e30524a9a1 \
  --model 60db-quality --sample-rate 48000
```

---

## 4. The mental model (read this once)

Four facts the docs get wrong — internalize them and the rest is easy:

1. **REST `/tts-synthesize` returns NDJSON**, not a single JSON object. Each line is `{"result":{"audioContent":"<base64 LINEAR16 PCM>"}}`. The engine concatenates every line's PCM and wraps it as a mono 16-bit WAV for you.
2. **`output_format` is ignored** — the API always returns raw PCM. The engine is what makes a `.wav`.
3. **Allowed sample rates: `8000 / 16000 / 24000 / 48000` only.** `44100` is rejected with a `400`.
4. **Sample rate ≠ fidelity.** The model is band-limited to ~8 kHz, so `48000` is upsampled headroom — the voice can sound slightly "compressed." `enhance` and `60db-quality` do **not** raise that ceiling. If you need true full-band audio, use a full-band provider for that one job.

Also: **TTS text caps at 5000 chars** per request — longer scripts must be split and concatenated (see [Recipes](#6-recipes-cookbook)).

---

## 5. Commands in depth

### `doctor` — diagnose setup

```bash
python3 $E doctor
```

```
60db doctor
  python         3.11.9
  config path    /Users/you/.config/60db/config.json  (exists)
  api key        present (config)
  voice_id       fbb75ed2-975a-40c7-9e06-38e30524a9a1
  model          60db-quality
  sample_rate    48000 Hz
  output_format  wav
  websockets     not installed (only for --ws)
```

Exits non-zero if no key is found — handy as a setup gate in scripts.

---

### `voices` — list voice ids

```bash
python3 $E voices            # built-in + your cloned voices
python3 $E voices --mine     # only your cloned voices
python3 $E voices --json     # raw objects (for scripting)
```

```
built-in voices (0):
your cloned voices (3):
  fbb75ed2-975a-40c7-9e06-38e30524a9a1  Zara   [Hindi  female]
  7c1a9e02-...                          Arjun  [Hindi  male]
  9d4f00b1-...                          Maya   [English  female]
```

The id field is **`voice_id`** (a UUID); language/gender come from a `labels` object. Pass a `voice_id` as `--voice` to `tts`.

---

### `langs` — supported languages

```bash
python3 $E langs            # TTS languages (30)
python3 $E langs --stt      # STT languages (39 + auto)
python3 $E langs --stt --json
```

```
STT languages (39):
  en    English
  hi    Hindi
  es    Spanish
  ...
```

Use these codes for `tts --voice` cloning languages and `stt --language`.

---

### `tts` — text → WAV

```bash
python3 $E tts "<text or path to .txt>" [--out FILE] [--voice ID] [--model M] \
  [--sample-rate HZ] [--speed 0.5-2.0] [--stability 0-100] [--similarity 0-100] \
  [--no-enhance] [--ws]
```

The first argument is either literal text **or a path to a `.txt` file** (auto-detected).

```bash
# Literal text → default out/voiceover.wav
python3 $E tts "Welcome to the show." --voice fbb75ed2-...

# A script file, custom output, slower delivery
python3 $E tts intro.txt --voice fbb75ed2-... --out out/intro.wav --speed 0.95
```

```
wrote out/intro.wav  (412160 B PCM, ~4.3s @ 48000Hz, REST, model=60db-quality, enhance=True)
```

**Parameters:**

| Flag | Range | What it does |
|------|-------|--------------|
| `--voice` | voice_id | Which voice. Required (CLI flag, config, or `init --voice`). |
| `--model` | `60db-quality` / base | Quality tier. `60db-quality` is the highest. |
| `--sample-rate` | 8000/16000/24000/48000 | Output rate. **Not** fidelity — see §4. |
| `--speed` | 0.5–2.0 | Talking speed; `1.0` is natural. |
| `--stability` | 0–100 | Higher = more consistent/monotone; lower = more expressive/variable. |
| `--similarity` | 0–100 | How tightly it hugs the reference voice. |
| `--no-enhance` | — | Turns off post-enhancement (on by default). |
| `--ws` | — | Legacy WebSocket stream (needs `websockets`); capped at the rate menu. |

The WAV is **mono, 16-bit LINEAR16**. Duration in the receipt is computed from PCM length.

---

### `stt` — audio → transcript

```bash
python3 $E stt <audio> [--language CODE] [--diarize] [--timestamps] \
  [--confidence] [--context "hints"] [--out FILE] [--json]
```

Audio ≤ 10 MB, ≤ 1 hour. Formats: WAV, MP3, M4A, OGG, FLAC, WebM, MP4. Language auto-detects when omitted.

```bash
# Plain transcript (auto-detect language)
python3 $E stt recording.mp3

# Speakers + word timings, save text to a file
python3 $E stt interview.m4a --diarize --timestamps --out interview.txt

# Full structured response (segments, words, confidences) as JSON
python3 $E stt call.wav --diarize --timestamps --confidence --json > call.json
```

```
[English, 42.7s] So the first thing we noticed was the latency...
wrote transcript -> interview.txt
```

| Flag | What it does |
|------|--------------|
| `--language` | ISO 639-1 code (`en`, `hi`, …). Omit for auto-detect. |
| `--diarize` | Label speakers (Speaker 0 / Speaker 1 / …). |
| `--timestamps` | Word-level start/end times (in the JSON `words[]`). |
| `--confidence` | Per-word confidence scores. |
| `--context` | Domain/speaker hints (names, jargon) to boost accuracy. |
| `--out` | Write the plain transcript text to a file. |
| `--json` | Print the full response object. |

---

### `clone` — create a cloned voice ⚠️ unverified

> The clone endpoint is **doc-only** and the docs contradict each other on how audio is submitted (multipart `files[]` vs a single `sample_url`). **Test on your workspace before relying on it.** Free tier allows 0 clones; Pro 5; Enterprise unlimited.

```bash
# Multipart path (default): 3–10 samples, 10–60s each, >= 2 min total
python3 $E clone --name "Brand VO" --sample a.wav --sample b.wav --sample c.wav \
  --language en --gender female --description "warm narrator"

# URL path (alternative): one hosted sample
python3 $E clone --name "Brand VO" --sample-url https://example.com/sample.wav
```

```
clone submitted: id=voice-custom-123  status=processing
cloning is async (~10-15 min). Re-run `voices --mine` to see when status -> ready.
```

Poll with `voices --mine` until `status -> ready`.

---

### `delete-voice` — remove a cloned voice ⚠️ irreversible

```bash
python3 $E delete-voice <voice_id>
```

```
Voice deleted successfully
```

Hard delete; only your own custom voices.

---

### `chat` — the LLM core for voice agents

60db has **no native calling/telephony API**. You build a voice agent from parts: `stt` (ears) + `chat` (brain) + `tts` (mouth). `chat` is an OpenAI-style completion against `60db-tiny`.

```bash
python3 $E chat "Summarize attachment theory in one line."
python3 $E chat "What's a good greeting?" --system "You are a terse phone receptionist."
```

```
Attachment theory explains how early caregiver bonds shape adult relationship patterns.

[chat_id=chat_a1b2c3  (pass --chat-id to continue)]
```

Pass the printed `chat_id` back to keep conversational memory:

```bash
python3 $E chat "And in two lines?" --chat-id chat_a1b2c3
```

---

## 6. Recipes (cookbook)

### A. Narrate a script longer than 5000 chars

`/tts-synthesize` caps at 5000 chars. Split on blank lines, synthesize each chunk, then concatenate the WAVs (stdlib `wave`, no external dep):

```bash
E=skills/60db/scripts/sixtydb.py
VOICE=fbb75ed2-975a-40c7-9e06-38e30524a9a1
mkdir -p out/parts

# 1. split long.txt into ~4000-char chunks on paragraph boundaries
python3 - <<'PY'
import textwrap, pathlib
text = pathlib.Path("long.txt").read_text()
chunks, buf = [], ""
for para in text.split("\n\n"):
    if len(buf) + len(para) > 4000:
        chunks.append(buf); buf = ""
    buf += para + "\n\n"
if buf.strip(): chunks.append(buf)
for i, c in enumerate(chunks):
    pathlib.Path(f"out/parts/{i:03d}.txt").write_text(c)
print(len(chunks), "chunks")
PY

# 2. synthesize each chunk
for f in out/parts/*.txt; do
  python3 $E tts "$f" --voice "$VOICE" --out "${f%.txt}.wav"
done

# 3. concatenate the WAVs into one file
python3 - <<'PY'
import wave, glob, pathlib
files = sorted(glob.glob("out/parts/*.wav"))
out = wave.open("out/full.wav", "wb")
for i, f in enumerate(files):
    w = wave.open(f, "rb")
    if i == 0: out.setparams(w.getparams())
    out.writeframes(w.readframes(w.getnframes())); w.close()
out.close()
print("wrote out/full.wav")
PY
```

### B. Subtitles with word-level timing

```bash
python3 $E stt talk.mp4 --timestamps --json > talk.json
# talk.json → words[] each with {word, start, end}; feed into your SRT/VTT builder
```

### C. A minimal voice-agent turn (ears → brain → mouth)

```bash
E=skills/60db/scripts/sixtydb.py
VOICE=fbb75ed2-975a-40c7-9e06-38e30524a9a1

USER_TEXT=$(python3 $E stt caller.wav --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["text"])')
REPLY=$(python3 $E chat "$USER_TEXT" --system "You are a concise support agent." --chat-id call-42 | head -1)
python3 $E tts "$REPLY" --voice "$VOICE" --out out/reply.wav
# play it back: afplay out/reply.wav   (macOS)   |   aplay out/reply.wav (Linux)
```

Loop this per turn, reusing one `--chat-id` for memory. Wire the audio I/O to your telephony stack (Twilio, LiveKit, a SIP trunk) — 60db supplies the voice + brain, not the dialer.

### D. Batch a folder of scripts

```bash
for f in scripts/*.txt; do
  python3 $E tts "$f" --voice "$VOICE" --out "out/$(basename "${f%.txt}").wav"
done
```

### E. Multilingual voiceover

```bash
python3 $E voices --json | python3 -c 'import json,sys; [print(v["voice_id"], v.get("labels",{}).get("language_name")) for v in json.load(sys.stdin)["cloned_voices"]]'
python3 $E tts hindi_script.txt --voice <hindi_voice_id> --out out/hi.wav
```

---

## 7. Errors & troubleshooting

| HTTP | Meaning | Fix |
|------|---------|-----|
| `401` | Bad/expired key | Re-run `init`, or rotate at app.60db.ai |
| `402` | Insufficient credits | Top up the workspace wallet |
| `413` | Payload too large | Text > 5000 chars, or audio > 10 MB — split it |
| `429` | Rate limited | Back off; honor `X-RateLimit-Reset` |
| `400` on `tts` | Off-menu sample rate | Use `8000 / 16000 / 24000 / 48000` only |

| Symptom | Cause → fix |
|---------|-------------|
| `no 60db API key found` | Not configured → `init` or `export SIXTYDB_API_KEY=…` |
| Audio is garbled/truncated | You parsed the response as one JSON blob → it's **NDJSON** (the engine handles this) |
| Voice sounds "compressed" | ~8 kHz model ceiling → expected; swap providers if you need full-band |
| `voices` shows `?` for an id | Voice object lacks `voice_id`/`id` → check `voices --json` |
| `--ws` errors immediately | `websockets` not installed → `pip install websockets` |

Run `python3 $E doctor` first whenever something's off. Full notes: [`skills/60db/references/troubleshooting.md`](skills/60db/references/troubleshooting.md).

---

## 8. Driving it through the agent

You normally don't type these commands — you type **`/60db`** and the agent runs them.

- **First run:** `/setup-60db` walks you through key entry (privately) and default selection, then verifies with `doctor`.
- **When a request is underspecified**, the agent asks one round of questions (use case · voice · model · kHz · format) before acting, then persists your answers as defaults.
- **Routing:** "voice over this script" → `tts`; "transcribe this call" → `stt`; "what voices do I have" → `voices`; "build a phone bot" → `chat` + `stt` + `tts`.

The deep API notes (verified vs. doc-only, field shapes, streaming) live in [`skills/60db/references/`](skills/60db/references/).
