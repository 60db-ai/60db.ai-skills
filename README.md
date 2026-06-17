# 60db — agent skill for the 60db.ai voice platform

A battle-tested [agent skill](https://docs.claude.com/en/docs/claude-code/skills) for [60db.ai](https://60db.ai): **text-to-speech, speech-to-text, voice cloning, voice management, language lookup, and LLM chat** (the conversational core for voice agents) — through one **zero-dependency** Python CLI. Triggered by `/60db`.

It encodes the things the docs get wrong, so you don't relearn them the hard way: the REST response is NDJSON (not a single JSON blob), only `8000/16000/24000/48000 Hz` are accepted (44100 is rejected), `output_format` is ignored, and "higher sample rate" does **not** mean "higher fidelity" (the model band-limits at ~8 kHz).

## What's in the box

```
skills/
├── 60db/                 # the worker skill (trigger: /60db)
│   ├── SKILL.md
│   ├── scripts/sixtydb.py   # stdlib-only CLI: init · doctor · tts · stt · voices
│   │                        #   · clone · delete-voice · langs · chat
│   └── references/          # tts · stt · voices · agents-calling · api · troubleshooting
└── setup-60db/           # first-run onboarding (trigger: /setup-60db)
    └── SKILL.md
```

Only `python3` (3.8+) is required. The optional legacy WebSocket TTS path (`--ws`) is the one thing that needs `pip install websockets`.

## Install

```bash
git clone https://github.com/uditgoenka/60db.git
cd 60db
./install.sh            # symlinks both skills into ~/.claude/skills (use --copy to copy)
```

Or install manually — copy `skills/60db` and `skills/setup-60db` into your agent's skills directory (`~/.claude/skills` for Claude Code, `~/.codex/skills` for Codex). Then **restart your agent session** so the new skills load.

Set `CLAUDE_SKILLS_DIR` to install elsewhere: `CLAUDE_SKILLS_DIR=~/.codex/skills ./install.sh`.

## First-time setup

Run **`/setup-60db`** (or directly):

```bash
python3 skills/60db/scripts/sixtydb.py init     # hidden prompt for your API key -> config (mode 600)
python3 skills/60db/scripts/sixtydb.py doctor   # verify
```

Get an API key at **app.60db.ai → Settings → Developer → API Keys**. The key is stored locally at `${XDG_CONFIG_HOME:-~/.config}/60db/config.json` (mode 600) **or** read from the env var `SIXTYDB_API_KEY`. It is never read from the command line, never printed, and never committed.

> **Security:** the key is yours to enter. Don't paste it into an agent chat — chat history is retained by the platform. If it ever leaks, rotate it at app.60db.ai.

## Quick start

```bash
E=skills/60db/scripts/sixtydb.py
python3 $E tts "Hello there." --out out/hello.wav          # text -> WAV (48 kHz, 60db-quality)
python3 $E tts script.txt --voice <id> --out out/vo.wav
python3 $E stt recording.mp3 --diarize --timestamps        # audio -> transcript
python3 $E voices                                          # list voice ids
python3 $E langs --stt                                      # 39 STT languages
python3 $E chat "One-line summary of attachment theory."   # LLM core for agents
python3 $E doctor                                          # diagnose setup
```

Settings resolve **CLI flag > env `SIXTYDB_*` > config file > built-in default**. Store defaults with `init --no-key --voice <id> --model 60db-quality --sample-rate 48000`.

## Coverage

| Use case | Command | Status |
|----------|---------|--------|
| Text-to-speech (REST + WS) | `tts` | ✅ verified |
| Speech-to-text (batch + streaming) | `stt` | ✅ endpoint verified, response shape per docs |
| List voices | `voices` | ✅ verified |
| Voice cloning | `clone` | ⚠️ doc-only (docs contradict — test first) |
| Update / delete voice | `delete-voice` | ⚠️ doc-only |
| Languages | `langs` | ✅ |
| LLM chat (voice-agent core) | `chat` | documented; no native calling API in 60db |

See `skills/60db/references/` for the full, sourced API notes — including which fields are verified vs. taken from the (partly inaccurate) docs.

## Why a skill, not just the SDK

60db publishes `npm i 60db` / `pip install 60db` SDKs, but the docs are inconsistent (placeholder OpenAPI, wrong TTS response schema, a 404'd voice-agent page). This skill is **stdlib-only** and pins the behavior that's actually true, so it keeps working regardless. The `references/troubleshooting.md` page is the antidote to relearning the same five mistakes.

## License

MIT © uditgoenka. Not affiliated with 60db.ai.
