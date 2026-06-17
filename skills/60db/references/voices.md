# Voices — list, clone, manage

## List `GET /voices` (verified by live calls)

Header `Authorization: Bearer <key>`. Response is a `data` object split into two arrays:

```json
{ "success": true, "message": "…",
  "data": {
    "built_in_voices": [ … ],
    "cloned_voices":   [ {
      "voice_id": "fbb75ed2-975a-40c7-9e06-38e30524a9a1",
      "name": "Zara",
      "category": "cloned",
      "model": "60db Fast",
      "labels": {"language":"hi","language_name":"Hindi","gender":"female","accent":"Indian"},
      "description": null,
      "preview_url": "/voices/audio/<voice_id>",
      "reference_text": "…",
      "is_native": true,
      "available_for_tiers": [],
      "categories": ["Conversational","IVR/Call Center", …]
    } ] } }
```

The identifier field is **`voice_id`** (a UUID) — **not** `id` — and language/gender live under **`labels`** (`labels.language`, `labels.language_name`, `labels.gender`, `labels.accent`), not at the top level. Pass `voice_id` as `--voice` to `tts`. (On one live workspace all 232 voices came back under `cloned_voices` with `built_in_voices` empty.)

> Earlier notes claimed a flat `{name, id, lang, gender}` shape — that was wrong; the live response is the rich object above. When docs and live data disagree, the live data wins.

```bash
python3 scripts/sixtydb.py voices            # built-in + your cloned (id + name + [lang gender])
python3 scripts/sixtydb.py voices --mine     # only your cloned voices
python3 scripts/sixtydb.py voices --json     # raw objects
```

## Clone `POST /voices` — ⚠️ UNVERIFIED, docs contradict each other

**Test before relying on this.** The docs disagree on how audio is submitted:

- **REST + features pages:** `multipart/form-data` with a `files[]` array — **3–10 files, 10–60 s each, ≥ 2 min total**, MP3/WAV/FLAC, 44.1 kHz+, clean speech. Optional `name` (req), `description`, `language`, `gender` (`male`/`female`/`neutral`).
- **MCP docs:** a single **`sample_url`** (one 30 s+ sample) instead.

The engine defaults to the multipart path and switches to JSON+`sample_url` if you pass `--sample-url`:

```bash
python3 scripts/sixtydb.py clone --name "Brand VO" --sample a.wav --sample b.wav --language en
python3 scripts/sixtydb.py clone --name "Brand VO" --sample-url https://…/sample.wav
```

Documented response (async): `{ "id":"voice-custom-123", "status":"processing", "is_custom":true, "estimated_completion":"…" }`. Cloning runs ~10–15 min; `status` goes `processing → ready | failed`. Poll with `voices --mine`. **No consent flag is documented** despite this being voice cloning — if the API requires one, it's undocumented. No webhook endpoint is published.

## Update `PUT /voices/{id}` — ⚠️ doc-only

Body `{name?, description?}` (only those two are mutable; language is not). Only custom voices; system voices can't be modified.

## Delete `DELETE /voices/{id}` — ⚠️ doc-only, irreversible

```bash
python3 scripts/sixtydb.py delete-voice <voice_id>
```

Returns `{"success":true,"message":"Voice deleted successfully"}`. **Hard delete.** Only your custom voices.

## Tier limits (features page, unverified)

| Tier | Custom voices |
|------|---------------|
| Free / Starter | 0 |
| Pro | 5 |
| Enterprise | "unlimited" |

## Languages for voices

`lang`/`gender` come back `null` on `/voices`. To filter or set a language on cloning, use codes from `GET /tts/languages` (30 TTS languages; see [api.md](api.md)).
