---
name: setup-60db
description: First-run setup for the 60db.ai voice skill — store the API key privately, choose voice/model/sample-rate/format defaults, and verify the connection. Run once before first use of /60db.
disable-model-invocation: true
---

# Set up 60db.ai

Idempotent first-run setup for the `/60db` skill. Explore → ask (one decision at a time) → write defaults → the user enters the key → verify. Re-run any time to change defaults or rotate the key.

**The engine lives in the sibling skill.** Resolve it once and reuse:

```bash
ENGINE="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)/60db/scripts/sixtydb.py"
# Claude Code default install: ~/.claude/skills/60db/scripts/sixtydb.py
[ -f "$ENGINE" ] || ENGINE="$HOME/.claude/skills/60db/scripts/sixtydb.py"
```

## Golden rule — the key is the user's to enter

**Never type, paste, print, log, or commit the user's API key.** You scaffold; the user supplies the secret. If they paste a key into chat, refuse to use it and tell them to rotate it at `app.60db.ai` and enter the fresh one locally. The key only ever reaches disk through the user-run `init` (hidden prompt) or env `SIXTYDB_API_KEY`.

## Phase 1 — Explore

```bash
python3 "$ENGINE" doctor    # python ok? config present? key present? defaults? websockets?
```

Read the output. If `config path … MISSING`, this is a fresh install → full onboarding. If a key is already present, this is a re-config → skip Phase 3 unless they want to rotate.

## Phase 2 — Ask the defaults (sequential, AskUserQuestion)

Walk these one at a time with the platform's blocking question tool. Each becomes a stored default. Don't dump all four at once.

1. **Primary use case** — TTS (narration/voiceover) · STT (transcription) · Voice cloning · Voice agent (chat+stt+tts). Sets which reference to surface and whether a voice id is needed now.
2. **Voice** (if TTS/cloning) — run `python3 "$ENGINE" voices` first, then offer the real voice ids by name. Store the chosen id.
3. **Model** — `60db-quality` (recommended, highest tier, honored by REST) or the base model.
4. **Sample rate (kHz)** — 48000 (recommended) · 24000 · 16000 · 8000. **Never offer 44100 — 60db rejects it.** Note that rate sets container headroom, not fidelity (the model band-limits ~8 kHz).
5. **Output format** — WAV (default) or raw PCM.

## Phase 3 — Store defaults, then have the user enter the key

Scaffold the non-secret defaults yourself (safe — touches no key):

```bash
python3 "$ENGINE" init --no-key --voice <id> --model 60db-quality --sample-rate 48000 --format wav
```

Then hand the key step to the **user** (pick the path that fits where they are):

- **They have a terminal on this host:** ask them to run `python3 "$ENGINE" init` — it prompts for the key at a hidden prompt (never echoed) and writes `${XDG_CONFIG_HOME:-~/.config}/60db/config.json` at mode 600.
- **Cloud / CI:** they set `SIXTYDB_API_KEY` through the platform's secret manager; the engine reads it from the env.

Tell them where to get the key: `https://app.60db.ai` → Settings → Developer → API Keys (keys look like `sk_live_…`).

## Phase 4 — Verify

```bash
python3 "$ENGINE" doctor          # should now show: api key present
python3 "$ENGINE" voices | head   # a real list confirms the key actually works (401 = bad key)
```

If `voices` 401s, the key is wrong/expired — back to Phase 3. If `402 insufficient credits`, the workspace wallet needs a top-up at app.60db.ai.

## Phase 5 — Done

Confirm what now works and point onward:

- `/60db` is live — TTS, STT, voices, clone, langs, chat.
- A 10-second smoke test: `python3 "$ENGINE" tts "Setup complete." --out out/ok.wav`
- Deeper docs live under the `60db` skill's `references/` (tts, stt, voices, agents-calling, api, troubleshooting).
