<div align="center">

# 60db.ai

**Drop [60db.ai](https://60db.ai) voice into [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [OpenAI Codex](https://developers.openai.com/codex), [OpenCode](https://opencode.ai), or any agent with a skills directory.**

Text-to-speech, speech-to-text, voice cloning, voice management, and the LLM core for voice agents — through one **zero-dependency** Python CLI. Triggered by `/60db`.

[![Claude Code Skill](https://img.shields.io/badge/Claude_Code-Skill-blue?logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code)
[![Codex](https://img.shields.io/badge/Codex-Skill-green?logo=openai&logoColor=white)](https://developers.openai.com/codex)
[![OpenCode](https://img.shields.io/badge/OpenCode-Skill-purple)](https://opencode.ai)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/uditgoenka/60db/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[![Powered by 60db.ai](https://img.shields.io/badge/Powered_by-60db.ai-ff5a5f)](https://60db.ai)
[![Follow @60dbai](https://img.shields.io/badge/Follow-@60dbai-000000?style=flat&logo=x&logoColor=white)](https://x.com/60dbai)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-60--db-0A66C2?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/company/60-db/)

<br>

*"Type `/60db` → pick a voice → ship audio"*

*The docs are partly wrong. This skill isn't — it pins the behavior that's actually true.*

**2 skills · 9 CLI subcommands · zero pip installs · every API gotcha pre-solved.**

<br>

[How It Works](#how-it-works) · [Commands](#commands) · [Gotchas](#gotchas-that-bite-everyone) · [Quick Start](#quick-start) · [References](skills/60db/references/) · [FAQ](#faq)

</div>

---

```
     SETUP             TTS              STT             VOICES            CLONE             CHAT
 ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
 │   Key    │     │  Text →  │     │ Audio →  │     │   List   │     │  Train   │     │   LLM    │
 │  Config  │────▶│   WAV    │────▶│  Script  │────▶│   Pick   │────▶│  a New   │────▶│   Core   │
 │  Doctor  │     │  48 kHz  │     │ Diarize  │     │  Voice   │     │  Voice   │     │ for Bots │
 └──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
  init·doctor         tts              stt             voices            clone             chat

 ┌──────────┐     ┌──────────┐     ┌──────────┐
 │  Langs   │     │  Delete  │     │  Setup   │
 │  Lookup  │     │    a     │     │  Wizard  │
 │ TTS/STT  │     │  Voice   │     │ /setup   │
 └──────────┘     └──────────┘     └──────────┘
    langs        delete-voice      setup-60db
```

---

## Why This Exists

60db.ai ships great voices and a fast API — but the published docs get the wiring **wrong**, and a previous build relearned every mistake the hard way: the REST response isn't a JSON blob, the sample-rate menu is shorter than documented, the format flag is a no-op, and "higher kHz" doesn't mean "higher fidelity."

This skill **encodes the truth** so you never relearn it. It is **stdlib-only** Python — no `requests`, no SDK, no version drift — and every endpoint is annotated *verified* vs. *doc-only*, with the live-API findings winning whenever they disagree with the docs.

The five mistakes it pins so you skip them:

1. **REST `/tts-synthesize` returns NDJSON** — concatenate each line's `result.audioContent` (base64 LINEAR16 PCM), not one JSON object.
2. **Only `8000 / 16000 / 24000 / 48000 Hz` are accepted** — `44100` is rejected.
3. **`output_format` is ignored** — the API always returns raw PCM; wrap it as WAV yourself.
4. **Sample rate ≠ fidelity** — the model band-limits at ~8 kHz, so 48 kHz is upsampled headroom; `enhance` and `60db-quality` do **not** raise the ceiling.
5. **The voice id field is `voice_id`, not `id`**, and language/gender live under `labels` — confirmed by live inspection, contradicting the docs.

---

## How It Works

One CLI — `skills/60db/scripts/sixtydb.py` (stdlib only, Python 3.8+) — fronts every 60db.ai use case against `https://api.60db.ai`.

```
/60db
  1. Setup once     →  user runs `init`: hidden key prompt → config (mode 600)
  2. Ask if unclear →  AskUserQuestion: use case · voice · model · kHz · format
  3. Route          →  tts / stt / voices / clone / chat / langs / doctor
  4. Verify         →  `doctor` reports key presence + resolved defaults (never prints the key)
```

Every setting resolves the same way, so you can override per-call or store defaults once:

```
CLI flag  >  env SIXTYDB_*  >  config file  >  built-in default
```

### Setup is the user's job

The API key is **never** typed by the agent, never passed on the command line, never printed, never committed. The user runs `init` (a hidden prompt) or sets `SIXTYDB_API_KEY`. In a chat session where the user can't reach a hidden prompt, the agent scaffolds defaults with `init --no-key` and hands the key step back to the user.

---

## Commands

Two skills install from this repo:

| Skill | Trigger | What it does |
|-------|---------|--------------|
| **60db** | `/60db` | The worker — routes every voice use case to the CLI below |
| **setup-60db** | `/setup-60db` | First-run onboarding: collects the key privately, picks defaults, verifies |

The worker drives one CLI with **9 subcommands**:

| Subcommand | What it does | Status |
|------------|--------------|--------|
| `init` | Hidden key prompt → config (mode 600); `--no-key` stores defaults only | ✅ |
| `doctor` | Diagnose setup — key presence (never revealed), resolved defaults | ✅ |
| `tts` | Text or `.txt` → WAV (REST NDJSON; `--ws` for legacy WebSocket) | ✅ verified |
| `stt` | Audio → transcript (`--diarize`, `--timestamps`, `--json`) | ✅ endpoint verified |
| `voices` | List voice ids (built-in + your cloned), `--mine`, `--json` | ✅ verified |
| `clone` | Train a new voice from samples (`--sample` / `--sample-url`) | ⚠️ doc-only — test first |
| `delete-voice` | Hard-delete one of your custom voices | ⚠️ doc-only |
| `langs` | Supported languages (`--stt` for STT's 39) | ✅ |
| `chat` | LLM core (`60db-tiny`) you pair with stt+tts for a voice agent | documented |

**Only `python3` (3.8+) is required.** The optional legacy WebSocket TTS path (`--ws`) is the one thing that needs `pip install websockets`.

### Quick Decision Guide

| I want to... | Use |
|--------------|-----|
| Narration / voiceover from text | `tts "..." --out out/vo.wav` |
| Read a script file aloud | `tts script.txt --voice <id> --out out/vo.wav` |
| Transcribe audio with speaker labels | `stt rec.mp3 --diarize --timestamps` |
| See which voices I can use | `voices` (then `voices --mine`) |
| Use a specific language | `langs` / `langs --stt` |
| Clone my own brand voice | `clone --name "Brand VO" --sample a.wav --sample b.wav` *(test first)* |
| Build a phone/voice bot | `chat` as the brain + `stt` ears + `tts` mouth (no native calling API) |
| Figure out why audio sounds "compressed" | `doctor` → [troubleshooting.md](skills/60db/references/troubleshooting.md) |
| Set up for the first time | `/setup-60db` |

---

## Gotchas That Bite Everyone

Full list in [references/troubleshooting.md](skills/60db/references/troubleshooting.md) — the antidote to relearning the same five mistakes.

| Symptom | Cause | Fix |
|---------|-------|-----|
| Output sounds a touch "compressed" | Model is ~16 kHz-native, band-limited to ~8 kHz | Expected; `enhance`/`60db-quality` don't lift it — swap to a full-band provider if you need it |
| Garbled / truncated audio | REST returns **NDJSON**, not one JSON blob | Concatenate every line's `result.audioContent` (base64 LINEAR16) |
| `400` on synthesize | Sample rate `44100` (or anything off-menu) | Use `8000 / 16000 / 24000 / 48000` only |
| Format flag seems ignored | `output_format` **is** ignored — always raw PCM | Wrap the PCM as WAV yourself (the CLI does) |
| Long script cut off | TTS caps at **5000 chars** per request | Split, synthesize, concatenate WAVs |
| `voices` prints `None` for the id | Field is `voice_id`, language/gender under `labels` | Read `voice_id`; the CLI already handles this |
| `no API key found` | Key not in config or env | Run `init`, or export `SIXTYDB_API_KEY` |

---

## Quick Start

### Claude Code

**Option A — npx install (recommended):**

```bash
npx skills add uditgoenka/60db
```

Installs both the `60db` and `setup-60db` skills. **Restart your agent session** so they load, then run `/setup-60db`.

**Option B — Guided installer:**

```bash
git clone https://github.com/uditgoenka/60db.git
cd 60db
./install.sh                 # symlinks both skills into ~/.claude/skills (--copy to copy instead)
```

Install elsewhere with `CLAUDE_SKILLS_DIR=~/.codex/skills ./install.sh`.

**Option C — Manual copy:**

```bash
git clone https://github.com/uditgoenka/60db.git

# Claude Code
cp -r 60db/skills/60db        ~/.claude/skills/60db
cp -r 60db/skills/setup-60db  ~/.claude/skills/setup-60db
```

> **Note:** Start a **new** session after installing — skills are only picked up on session start. This is an agent-platform limitation, not a bug.

### Codex / OpenCode / other agents

Copy the same two skill folders into that agent's skills directory:

```bash
git clone https://github.com/uditgoenka/60db.git
cp -r 60db/skills/60db 60db/skills/setup-60db  ~/.codex/skills/          # Codex
# or use:  CLAUDE_SKILLS_DIR=~/.config/opencode/skills ./install.sh      # OpenCode
```

The skill is plain markdown + stdlib Python, so it runs anywhere; only `AskUserQuestion`-style prompting is Claude-specific and degrades gracefully.

### First-time setup

Run **`/setup-60db`**, or directly:

```bash
E=skills/60db/scripts/sixtydb.py
python3 $E init        # hidden prompt for your API key → config (mode 600)
python3 $E doctor      # verify (reports key presence without revealing it)
```

Get a key at **app.60db.ai → Settings → Developer → API Keys**. It is stored locally at `${XDG_CONFIG_HOME:-~/.config}/60db/config.json` (mode 600) **or** read from `SIXTYDB_API_KEY`. It is never read from the command line, never printed, and never committed.

> **Security:** the key is yours to enter. Don't paste it into an agent chat — chat history is retained by the platform. If it ever leaks, rotate it at app.60db.ai.

### Run It

```bash
E=skills/60db/scripts/sixtydb.py
python3 $E tts "Hello there." --out out/hello.wav          # text → WAV (48 kHz, 60db-quality)
python3 $E tts script.txt --voice <id> --out out/vo.wav
python3 $E stt recording.mp3 --diarize --timestamps        # audio → transcript
python3 $E voices                                          # list voice ids
python3 $E langs --stt                                      # 39 STT languages
python3 $E chat "One-line summary of attachment theory."   # LLM core for agents
python3 $E doctor                                          # diagnose setup
```

Store defaults once so you stop repeating flags:

```bash
python3 $E init --no-key --voice <id> --model 60db-quality --sample-rate 48000
```

---

## Coverage

| Use case | Command | Status |
|----------|---------|--------|
| Text-to-speech (REST + WS) | `tts` | ✅ verified |
| Speech-to-text (batch + streaming) | `stt` | ✅ endpoint verified, response shape per docs |
| List voices | `voices` | ✅ verified (live-corrected to `voice_id` / `labels`) |
| Voice cloning | `clone` | ⚠️ doc-only — docs contradict, test first |
| Update / delete voice | `delete-voice` | ⚠️ doc-only |
| Languages | `langs` | ✅ |
| LLM chat (voice-agent core) | `chat` | documented; no native calling API in 60db |

See [`skills/60db/references/`](skills/60db/references/) for the full, sourced API notes — including exactly which fields are verified vs. taken from the (partly inaccurate) docs.

---

## Repository Structure

```
60db/
├── README.md
├── LICENSE
├── install.sh                              ← symlink/copy installer (CLAUDE_SKILLS_DIR override)
├── .gitignore                              ← excludes config.json, *.env, out/, *.wav
└── skills/
    ├── 60db/                               ← the worker skill (trigger: /60db)
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   └── sixtydb.py                  ← stdlib-only CLI (9 subcommands)
    │   └── references/
    │       ├── tts.md                      ← NDJSON, rates, fidelity ceiling, WS
    │       ├── stt.md                      ← POST /stt params, streaming
    │       ├── voices.md                   ← real voice_id / labels shape; clone caveats
    │       ├── agents-calling.md           ← no native calling API; build from stt+chat+tts
    │       ├── api.md                       ← auth, errors, limits, languages, SDKs, pricing
    │       └── troubleshooting.md           ← the five mistakes, pre-solved
    └── setup-60db/                         ← first-run onboarding (trigger: /setup-60db)
        └── SKILL.md
```

---

## Why a Skill, Not Just the SDK

60db publishes `npm i 60db` / `pip install 60db` SDKs, but the docs are inconsistent — a placeholder OpenAPI ("Plant Store"), a wrong TTS response schema, a 404'd voice-agent page, and a clone endpoint that contradicts itself. This skill is **stdlib-only** and pins the behavior that's actually true against the live API, so it keeps working regardless of doc drift. `references/troubleshooting.md` is the part you'll thank it for.

---

## FAQ

**Q: How do I install it the fastest way?**
A: `npx skills add uditgoenka/60db`, then restart your agent and run `/setup-60db`.

**Q: Where does my API key go? Is it safe?**
A: Into a local config at `${XDG_CONFIG_HOME:-~/.config}/60db/config.json` (mode 600), or the `SIXTYDB_API_KEY` env var. It's never passed on the command line, never printed, and `.gitignore` keeps it out of git. The agent never types it for you.

**Q: My voice sounds slightly "compressed" at 48 kHz. Bug?**
A: No. The model is ~16 kHz-native and band-limited to ~8 kHz, so 48 kHz is upsampled headroom. `enhance` and `60db-quality` don't raise the ceiling. Need true full-band? Use a full-band provider for that one job.

**Q: Why does my saved audio come out garbled?**
A: The REST `/tts-synthesize` response is **NDJSON**, not a single JSON object. Concatenate every line's `result.audioContent` (base64 LINEAR16 PCM). The CLI does this for you.

**Q: Which sample rates are allowed?**
A: `8000`, `16000`, `24000`, `48000` only. `44100` is rejected.

**Q: Can 60db make or receive phone calls?**
A: There is **no native calling/telephony API**. You build a voice agent from the parts: `stt` (ears) + `chat` (brain, `60db-tiny`) + `tts` (mouth). See [agents-calling.md](skills/60db/references/agents-calling.md).

**Q: Is voice cloning reliable?**
A: The `clone` / `delete-voice` endpoints are **doc-only** and the docs contradict each other on how audio is submitted (multipart `files[]` vs. a single `sample_url`). The CLI supports both paths — **test before relying on it.**

**Q: Does it work outside Claude Code?**
A: Yes — it's markdown + stdlib Python. Copy the two skill folders into Codex's or OpenCode's skills directory. Only the `AskUserQuestion` onboarding prompt is Claude-specific and degrades gracefully.

**Q: Do I need the SDK or `requests`?**
A: No. Only `python3` 3.8+. The single optional dependency is `websockets`, used solely by the legacy `--ws` TTS path.

---

## Contributing

Contributions welcome — especially confirming the **doc-only** endpoints (`clone`, `delete-voice`, STT streaming) against live workspaces and turning them into verified anchors. Keep the CLI stdlib-only.

---

## Star History

<a href="https://www.star-history.com/?repos=uditgoenka%2F60db&type=timeline&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/image?repos=uditgoenka/60db&type=timeline&theme=dark&legend=bottom-right" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/image?repos=uditgoenka/60db&type=timeline&legend=bottom-right" />
   <img alt="Star History Chart" src="https://api.star-history.com/image?repos=uditgoenka/60db&type=timeline&legend=bottom-right" />
 </picture>
</a>

---

## License

MIT — see [LICENSE](LICENSE). Not affiliated with 60db.ai.

---

## Credits

- **[60db.ai](https://60db.ai)** — for the voice platform ([docs.60db.ai](https://docs.60db.ai))
- **[Anthropic](https://anthropic.com)** — for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and the skills system

---

<div align="center">

## Built & Maintained by the 60db.ai Team

This skill is built and maintained by the **[60db.ai](https://60db.ai)** team — so the platform is a first-class citizen inside your coding agent.

**[60db.ai](https://60db.ai)** — studio-quality AI voice for developers and creators: text-to-speech, speech-to-text, and voice cloning through one API. 1000+ voices, 30+ languages, ~150 ms latency, pay-as-you-go with $10 free credit. *"Transform text into lifelike speech in milliseconds."*

### Also from the team

- **[Qcall.ai](https://qcall.ai)** — AI voice agents that automate inbound & outbound phone calls (sales outreach, support, appointment scheduling). 15+ languages with mid-call switching, sentiment analysis and call recordings, CRM / calendar / helpdesk integrations, 24/7. *"Smarter calls. Better conversations."*
- **[Zeplo.ai](https://zeplo.ai)** — another AI product from the same team.

**Connect:** [60db.ai](https://60db.ai) · [docs.60db.ai](https://docs.60db.ai) · [@60dbai](https://x.com/60dbai) · [LinkedIn](https://www.linkedin.com/company/60-db/)

> *"Set the goal, mechanize the verification, and let the agent ship the audio."*

</div>
