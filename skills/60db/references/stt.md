# STT — speech-to-text

Batch transcription of an audio file, or realtime via WebSocket. One transcription model: **`60db-stt-v01`** ("non-hallucinating", 39 languages, diarization, word timestamps, code-switching, telephony μ-law).

## Batch `POST /stt` (multipart/form-data)

Header: `Authorization: Bearer <key>`. Audio **≤ 10 MB, ≤ 1 hr**. Formats: WAV, MP3, M4A, OGG, FLAC, WebM, MP4.

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `file` | file | — | the audio (multipart) |
| `language` | string | auto | ISO 639-1, or omit / `"auto"` to detect across 39 langs |
| `languages` | string | — | CSV of candidate codes to constrain detection |
| `diarize` | bool | false | speaker identification |
| `min_speakers` / `max_speakers` | int | — | diarization bounds |
| `return_timestamps` | string | `"none"` | `"none"` or `"word"` |
| `include_confidence` | bool | false | per-word confidence |
| `context` | string | — | domain / speaker / jargon hints — boosts accuracy |
| `keywords` | string | — | CSV, optional `:weight` per term (vocab boost) |
| `script_correction` | bool | false | Devanagari/Latin normalization |

Response (documented shape — confirm field casing against a live call):

```json
{
  "request_id": "…", "text": "full transcript",
  "language": "en", "language_name": "English",
  "duration_sec": 12.4, "snr_db": 28.1, "processing_ms": 800, "rtf": 0.06,
  "segments": [{ "start": 0.0, "end": 3.2, "text": "…", "confidence": 0.97,
                 "words": [{"word":"…","start":0.0,"end":0.3,"confidence":0.99}],
                 "speakers": [{"speaker":"S1","start":0.0,"end":3.2}] }],
  "words": [ … ],
  "warnings": [], "language_detection": {"mode":"…","candidates":["en","hi"]}
}
```

Word timings appear only with `return_timestamps="word"`; confidence only with `include_confidence=true`.

### Support endpoints

- `GET /stt/languages` → `{data:{languages[], total, features}}`. 39 languages + an `auto` entry (first element `{"code":"auto","name":"Auto-detect"}`); each carries `native`, `code_switching`, sometimes `wer_target`.
- `GET /stt/models` → one model, `60db-stt-v01`.

## Streaming `wss://api.60db.ai/ws/stt`

Auth query param: `?apiKey=sk_live_…` (or `?token=<jwt>&workspace_id=…`). Wait for server `connecting` → `connected` → `connection_established` before sending `start`.

```json
// client
{"type":"start","languages":["en","hi"],"config":{"encoding":"linear","sample_rate":48000,"utterance_end_ms":500,"continuous_mode":true}}
{"type":"audio","audio":"<base64 PCM or μ-law>","encoding":"linear","sample_rate":48000}
// or raw binary μ-law frames (480 B = 60 ms @ 8 kHz) for telephony
// server
{"type":"transcription","text":"Hello, how are you?","confidence":0.87,"language":"en","is_final":true}
{"type":"session_stopped","billing_summary":{"total_duration_seconds":12.4,"total_cost":0.00062}}
```

`languages` max 5/session; `sample_rate` ∈ {8000,16000,24000,44100,48000}; `encoding` `"linear"` (16-bit PCM) or `"mulaw"`; utterance timeout default 500 ms (min 300).

## CLI

```bash
python3 scripts/sixtydb.py stt recording.mp3                        # auto language, plain text
python3 scripts/sixtydb.py stt call.wav --diarize --timestamps      # speakers + word times
python3 scripts/sixtydb.py stt clip.m4a --language hi --json --out transcript.txt
python3 scripts/sixtydb.py stt clip.wav --context "Cricket coaching. Players: Arjun, Ishaan."
```
