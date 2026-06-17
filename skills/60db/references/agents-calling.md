# Voice agents & calling

**60db has no native calling / telephony / agent API.** There is no agent-create endpoint, no place-a-call endpoint, no phone-number / SIP / WebRTC provisioning, and no agent webhooks. The docs' `integration/livekit` page (the one place a realtime voice-agent pipeline would live) currently **404s**.

What 60db gives you is the **building blocks** — you assemble the loop yourself:

```
caller audio ──▶ STT (/ws/stt, μ-law telephony frames)
                   │  transcript
                   ▼
            LLM  POST /v1/chat/completions   (tool calling + chat_id memory)
                   │  reply text
                   ▼
                 TTS (/tts-synthesize or /ws/tts) ──▶ audio back to caller
```

60db is **telephony-ready as a component** (`60db-stt-v01` lists `telephony_mulaw` + `websocket_streaming`; the STT WS accepts raw μ-law frames). Bring your own call transport (Twilio, LiveKit, a SIP gateway) and pipe its audio through these primitives.

## LLM core `POST /v1/chat/completions` (OpenAI-style)

Header `Authorization: Bearer <key>`. Body:

| Field | Notes |
|-------|-------|
| `model` | e.g. `60db-tiny` |
| `messages` | `[{role, content}]` — `system` then `user`/`assistant` |
| `stream` | bool |
| `tool` | array — **function/tool calling supported** |
| `chat_id` | continue a saved conversation (history kept when `save_chat:true`) |

Response: `{id, choices:[{message:{role,content}}], usage, chat_id, response_time_ms}`.

```bash
python3 scripts/sixtydb.py chat "Greet the caller and ask how you can help."
python3 scripts/sixtydb.py chat "And their account balance?" --chat-id <id>   # continue
python3 scripts/sixtydb.py chat "Reply in one sentence." --system "You are a calm support agent."
```

## Knowledge / memory

The `/memory/*` endpoints (collections, ingest, search, context) can back an agent's knowledge. Not wrapped in the CLI yet — call directly with a Bearer token; see the memory pages under `docs.60db.ai`.

## Gaps

- `integration/livekit` is listed in `llms.txt` but returns HTTP 404 — if an official voice-agent recipe exists, it lives there and is currently inaccessible. Check in a browser or ask 60db.
- The `/v1/` prefix on chat vs the un-prefixed `/stt`, `/tts-synthesize` is a real inconsistency in the docs — confirm against the live API.
- Generic `POST /webhooks` exist (account-level), but they are **not** call/agent event hooks.
