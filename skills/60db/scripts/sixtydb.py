#!/usr/bin/env python3
"""60db.ai voice platform client — TTS, STT, voice cloning, voice management, chat.

One zero-dependency CLI (stdlib only) for the whole 60db.ai surface. The legacy
WebSocket TTS path is the *only* thing that needs the optional `websockets`
package; everything else runs on a bare Python 3.8+.

Credentials are NEVER read from argv and NEVER printed. The key lives in the
config file (written once by `init` at a hidden prompt) or in the env var
SIXTYDB_API_KEY. `init` is the only writer of the key.

Subcommands:
    init          store the API key (hidden prompt) + non-secret defaults
    doctor        diagnose setup (key present? defaults? ws?) — never prints the key
    voices        list voices (built-in + your cloned voices)
    langs         list supported languages (TTS by default, --stt for STT)
    tts           text -> WAV  (REST non-streaming by default; --ws legacy stream)
    stt           audio -> transcript (diarization, word timings, 39 languages)
    clone         create a cloned voice from audio sample(s)  [UNVERIFIED endpoint]
    delete-voice  delete one of your cloned voices (irreversible)
    chat          one-shot LLM completion (the conversational core for voice agents)

Config resolution everywhere: CLI flag > env (SIXTYDB_*) > config file > built-in default.
"""
import argparse
import base64
import importlib.util
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
import wave
from pathlib import Path

API_HOST = "https://api.60db.ai"
REST_TTS_URL = f"{API_HOST}/tts-synthesize"
WS_TTS_URL = "wss://api.60db.ai/ws/tts"
VOICES_URL = f"{API_HOST}/voices"
STT_URL = f"{API_HOST}/stt"
CHAT_URL = f"{API_HOST}/v1/chat/completions"

# Built-in defaults (lowest precedence). 60db (Inworld backend) supports only
# 8000 / 16000 / 24000 / 48000 Hz — 44100 is rejected. 48k is the REST native rate.
DEFAULTS = {
    "voice_id": "",
    "model": "60db-quality",     # highest 60db tier; honored by REST /tts-synthesize
    "sample_rate": 48000,
    "output_format": "wav",
    "speed": 1.0,
    "stability": 50,
    "similarity": 75,
    "enhance": True,
    "chat_model": "60db-tiny",
}
WS_SAMPLE_RATES = (8000, 16000, 24000, 48000)
TTS_TEXT_LIMIT = 5000            # /tts-synthesize hard cap per request


# ----------------------------------------------------------------------------- config
def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "60db" / "config.json"


def load_config() -> dict:
    p = config_path()
    if p.is_file():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_config(cfg: dict) -> Path:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=2) + "\n")
    os.chmod(p, 0o600)            # owner read/write only — it holds the key
    return p


def get_api_key(cfg: dict) -> str:
    """Key from env (CI-friendly) first, then config. NEVER from argv. NEVER printed."""
    key = (os.environ.get("SIXTYDB_API_KEY") or cfg.get("apiKey") or "").strip()
    if not key:
        sys.exit(
            "ERROR: no 60db API key found.\n"
            "  Run:  python3 sixtydb.py init        (prompts privately, never echoed)\n"
            "  or:   export SIXTYDB_API_KEY=sk_live_...\n"
            "Get a key at https://app.60db.ai  (Settings -> Developer -> API Keys)."
        )
    return key


def resolve(name: str, cli_val, cfg: dict):
    """CLI flag > env SIXTYDB_<NAME> > config > built-in default."""
    if cli_val is not None:
        return cli_val
    env = os.environ.get(f"SIXTYDB_{name.upper()}")
    if env:
        return env
    if name in cfg and cfg[name] not in (None, ""):
        return cfg[name]
    return DEFAULTS.get(name)


# ----------------------------------------------------------------------------- http
def _auth_headers(key: str, extra: dict | None = None) -> dict:
    h = {"Authorization": f"Bearer {key}"}
    if extra:
        h.update(extra)
    return h


def _send(req: urllib.request.Request, timeout: int = 300) -> bytes:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        hints = {401: " (bad/expired key)", 402: " (insufficient credits — top up the workspace wallet)",
                 413: " (payload too large — text > 5000 chars or audio > 10 MB)",
                 429: " (rate limited — back off / honor X-RateLimit-Reset)"}
        detail = e.read().decode(errors="replace")[:500]
        sys.exit(f"ERROR from 60db (HTTP {e.code}{hints.get(e.code, '')}): {detail}")
    except urllib.error.URLError as e:
        sys.exit(f"ERROR: cannot reach {API_HOST}: {e.reason}")


def http_get(url: str, key: str) -> bytes:
    return _send(urllib.request.Request(url, headers=_auth_headers(key), method="GET"))


def http_post_json(url: str, key: str, payload: dict, timeout: int = 300) -> bytes:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers=_auth_headers(key, {"Content-Type": "application/json"}))
    return _send(req, timeout=timeout)


def http_delete(url: str, key: str) -> bytes:
    return _send(urllib.request.Request(url, headers=_auth_headers(key), method="DELETE"))


def http_post_multipart(url: str, key: str, fields: dict, files: list) -> bytes:
    """fields: {name: value} (None skipped). files: [(form_name, filepath)].
    stdlib multipart so there is no `requests` dependency."""
    boundary = f"----60db{uuid.uuid4().hex}"
    parts = bytearray()
    for name, val in fields.items():
        if val is None:
            continue
        parts += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                  f"{val}\r\n").encode()
    for name, fp in files:
        fp = Path(fp)
        ctype = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
        parts += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; "
                  f"filename=\"{fp.name}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
        parts += fp.read_bytes() + b"\r\n"
    parts += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url, data=bytes(parts), method="POST",
        headers=_auth_headers(key, {"Content-Type": f"multipart/form-data; boundary={boundary}"}))
    return _send(req, timeout=600)


# ----------------------------------------------------------------------------- audio
def write_wav(out_path: Path, pcm: bytes, sample_rate: int) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)        # mono
        w.setsampwidth(2)        # LINEAR16 = 16-bit
        w.setframerate(sample_rate)
        w.writeframes(pcm)


def read_text_arg(text_or_path: str) -> str:
    """A path -> file contents; otherwise the literal string."""
    p = Path(text_or_path)
    return p.read_text().strip() if p.is_file() else text_or_path.strip()


# ----------------------------------------------------------------------------- tts (REST)
def synth_rest(text: str, out_path: Path, voice_id: str, sample_rate: int, model: str,
               speed: float, stability: int, similarity: int, enhance: bool) -> None:
    """POST /tts-synthesize (non-streaming). The response is line-delimited JSON
    (NDJSON); each line carries base64 LINEAR16 PCM in result.audioContent. We
    concatenate the PCM and write a mono 16-bit WAV. The endpoint returns no
    sample-rate metadata, so `sample_rate` is the rate the PCM is written at."""
    key = get_api_key(load_config())
    if not text:
        sys.exit("ERROR: empty text.")
    if len(text) > TTS_TEXT_LIMIT:
        sys.exit(f"ERROR: text is {len(text)} chars; /tts-synthesize caps at {TTS_TEXT_LIMIT}. "
                 "Split into multiple requests and concatenate the WAVs.")
    if not voice_id:
        sys.exit("ERROR: no voice. Pass --voice <id>, run `init --voice <id>`, or `voices` to list ids.")

    payload = {"text": text, "voice_id": voice_id, "enhance": bool(enhance),
               "speed": speed, "stability": stability, "similarity": similarity}
    if model:
        payload["model"] = model
    raw = http_post_json(REST_TTS_URL, key, payload)

    pcm = bytearray()
    for line in raw.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        chunk = msg.get("result", {}).get("audioContent") or msg.get("audioContent")
        if chunk:
            pcm += base64.b64decode(chunk)
        elif "error" in msg:
            sys.exit(f"ERROR from 60db: {msg['error']}")
    if not pcm:
        sys.exit(f"ERROR: no audio in response: {raw[:300]!r}")

    write_wav(out_path, bytes(pcm), sample_rate)
    secs = len(pcm) / 2 / sample_rate
    print(f"wrote {out_path}  ({len(pcm)} B PCM, ~{secs:.1f}s @ {sample_rate}Hz, "
          f"REST, model={model or 'default'}, enhance={enhance})")


# ----------------------------------------------------------------------------- tts (WS legacy)
def synth_ws(text: str, out_path: Path, voice_id: str, sample_rate: int) -> None:
    """Legacy WebSocket stream. Band-limited (~8 kHz model ceiling). Needs the
    optional `websockets` package: python3 -m pip install websockets."""
    import asyncio
    if importlib.util.find_spec("websockets") is None:
        sys.exit("ERROR: --ws needs the `websockets` package: python3 -m pip install websockets")
    import websockets
    if sample_rate not in WS_SAMPLE_RATES:
        sys.exit(f"ERROR: WS sample_rate must be one of {WS_SAMPLE_RATES}; got {sample_rate}.")
    if not voice_id:
        sys.exit("ERROR: no voice. Pass --voice <id> or run `init --voice <id>`.")

    key = get_api_key(load_config())
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()] or [text]
    ctx = f"vo-{int(time.time())}"

    async def run() -> bytes:
        pcm = bytearray()
        async with websockets.connect(f"{WS_TTS_URL}?apiKey={key}", max_size=None) as ws:
            await _ws_expect(ws, "connection_established")
            await ws.send(json.dumps({"create_context": {
                "context_id": ctx, "voice_id": voice_id,
                "audio_config": {"audio_encoding": "LINEAR16", "sample_rate_hertz": sample_rate}}}))
            await _ws_expect(ws, "context_created")
            for ln in lines:
                await ws.send(json.dumps({"send_text": {"context_id": ctx, "text": ln}}))
            await ws.send(json.dumps({"flush_context": {"context_id": ctx}}))
            while True:
                msg = json.loads(await ws.recv())
                if "audio_chunk" in msg:
                    pcm += base64.b64decode(msg["audio_chunk"]["audioContent"])
                elif msg.get("flush_completed"):
                    break
                elif "error" in msg:
                    sys.exit(f"ERROR from 60db: {msg['error']}")
            await ws.send(json.dumps({"close_context": {"context_id": ctx}}))
        return bytes(pcm)

    pcm = asyncio.run(run())
    write_wav(out_path, pcm, sample_rate)
    print(f"wrote {out_path}  ({len(pcm)} B PCM, ~{len(pcm)/2/sample_rate:.1f}s @ {sample_rate}Hz, WS)")


async def _ws_expect(ws, key: str) -> None:
    while True:
        msg = json.loads(await ws.recv())
        if msg.get(key):
            return
        if "error" in msg:
            sys.exit(f"ERROR from 60db: {msg['error']}")


# ----------------------------------------------------------------------------- stt
def transcribe(audio_path: str, language: str | None, diarize: bool, timestamps: bool,
               confidence: bool, context: str | None, out_path: str | None, as_json: bool) -> None:
    """POST /stt (multipart). Audio <=10 MB, <=1 hr. Auto-detects across 39
    languages when language is omitted/auto."""
    key = get_api_key(load_config())
    p = Path(audio_path)
    if not p.is_file():
        sys.exit(f"ERROR: no such audio file: {audio_path}")
    fields = {
        "language": language or "auto",
        "diarize": "true" if diarize else None,
        "return_timestamps": "word" if timestamps else None,
        "include_confidence": "true" if confidence else None,
        "context": context,
    }
    data = json.loads(http_post_multipart(STT_URL, key, fields, [("file", str(p))]))
    if as_json:
        print(json.dumps(data, indent=2))
    text = data.get("text", "")
    if out_path:
        Path(out_path).write_text(text + "\n")
        print(f"wrote transcript -> {out_path}")
    if not as_json:
        lang = data.get("language_name") or data.get("language") or "?"
        dur = data.get("duration_sec")
        tag = f"{lang}, {dur:.1f}s" if isinstance(dur, (int, float)) else lang
        print(f"[{tag}] {text}")


# ----------------------------------------------------------------------------- voices
def list_voices(mine_only: bool, as_json: bool) -> None:
    key = get_api_key(load_config())
    data = json.loads(http_get(VOICES_URL, key))
    payload = data.get("data", data)
    built_in = payload.get("built_in_voices", []) or []
    cloned = payload.get("cloned_voices", []) or []
    if as_json:
        print(json.dumps({"built_in_voices": built_in, "cloned_voices": cloned}, indent=2))
        return
    if not mine_only:
        print(f"built-in voices ({len(built_in)}):")
        for v in built_in:
            print(_voice_line(v))
    print(f"your cloned voices ({len(cloned)}):")
    for v in cloned:
        print(_voice_line(v))


def _voice_line(v: dict) -> str:
    """The id field is `voice_id` (live), with `id` as a fallback; language/gender
    live under a `labels` object on most voices."""
    vid = v.get("voice_id") or v.get("id") or "?"
    labels = v.get("labels") or {}
    lang = labels.get("language_name") or labels.get("language") or v.get("lang") or ""
    gender = labels.get("gender") or v.get("gender") or ""
    tag = "  ".join(t for t in (lang, gender) if t)
    return f"  {vid}  {v.get('name')}" + (f"  [{tag}]" if tag else "")


def clone_voice(name: str, samples, description, language, gender, sample_url) -> None:
    """Create a cloned voice. UNVERIFIED endpoint — 60db docs conflict on the
    input method (multipart files[] vs a single sample_url). Defaults to the
    multipart path; pass --sample-url for the JSON/url path."""
    key = get_api_key(load_config())
    if sample_url:
        payload = {"name": name, "sample_url": sample_url}
        for k, v in (("description", description), ("language", language), ("gender", gender)):
            if v:
                payload[k] = v
        raw = http_post_json(VOICES_URL, key, payload)
    else:
        if not samples:
            sys.exit("ERROR: clone needs --sample <file> (repeatable: 3-10 files, >=2 min total) "
                     "or --sample-url <url>.")
        fields = {"name": name, "description": description, "language": language, "gender": gender}
        raw = http_post_multipart(VOICES_URL, key, fields, [("files", s) for s in samples])
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(raw.decode(errors="replace")[:500])
        return
    vid = data.get("id") or data.get("voice_id")
    print(f"clone submitted: id={vid}  status={data.get('status', '?')}")
    print("cloning is async (~10-15 min). Re-run `voices --mine` to see when status -> ready.")


def delete_voice(voice_id: str) -> None:
    key = get_api_key(load_config())
    raw = http_delete(f"{VOICES_URL}/{voice_id}", key)
    try:
        print(json.loads(raw).get("message", f"deleted {voice_id}"))
    except json.JSONDecodeError:
        print(f"deleted {voice_id}")


# ----------------------------------------------------------------------------- languages
def list_languages(stt: bool, as_json: bool) -> None:
    key = get_api_key(load_config())
    url = f"{API_HOST}/stt/languages" if stt else f"{API_HOST}/tts/languages"
    data = json.loads(http_get(url, key))
    payload = data.get("data", data)
    langs = payload.get("languages", payload) if isinstance(payload, dict) else payload
    if as_json or not isinstance(langs, list):
        print(json.dumps(payload, indent=2))
        return
    print(f"{'STT' if stt else 'TTS'} languages ({len(langs)}):")
    for L in langs:
        if isinstance(L, dict):
            code = L.get("code") or L.get("language_id") or L.get("id") or ""
            name = L.get("name") or L.get("language_name") or L.get("native") or ""
            print(f"  {code}\t{name}")
        else:
            print(f"  {L}")


# ----------------------------------------------------------------------------- chat (LLM core)
def chat(message: str, model: str, system: str | None, chat_id: str | None) -> None:
    """POST /v1/chat/completions (OpenAI-style). The conversational core you pair
    with stt + tts to build a voice agent (60db has no native calling API)."""
    key = get_api_key(load_config())
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": message}]
    payload = {"model": model, "messages": messages}
    if chat_id:
        payload["chat_id"] = chat_id
    data = json.loads(http_post_json(CHAT_URL, key, payload))
    choices = data.get("choices", [])
    if choices:
        print(choices[0].get("message", {}).get("content", ""))
    if data.get("chat_id"):
        print(f"\n[chat_id={data['chat_id']}  (pass --chat-id to continue)]")


# ----------------------------------------------------------------------------- doctor
def doctor() -> None:
    cfg = load_config()
    p = config_path()
    key = (os.environ.get("SIXTYDB_API_KEY") or cfg.get("apiKey") or "").strip()
    src = "env SIXTYDB_API_KEY" if os.environ.get("SIXTYDB_API_KEY") else ("config" if cfg.get("apiKey") else "?")
    print("60db doctor")
    print(f"  python         {sys.version.split()[0]}")
    print(f"  config path    {p}  ({'exists' if p.is_file() else 'MISSING — run init'})")
    print(f"  api key        {('present (' + src + ')') if key else 'NOT SET — run init'}")
    print(f"  voice_id       {resolve('voice_id', None, cfg) or '(none — set with init --voice)'}")
    print(f"  model          {resolve('model', None, cfg)}")
    print(f"  sample_rate    {resolve('sample_rate', None, cfg)} Hz")
    print(f"  output_format  {resolve('output_format', None, cfg)}")
    has_ws = importlib.util.find_spec("websockets") is not None
    print(f"  websockets     {'installed (legacy --ws available)' if has_ws else 'not installed (only for --ws)'}")
    if not key:
        sys.exit(1)


# ----------------------------------------------------------------------------- init
def cmd_init(args) -> None:
    cfg = load_config()
    if not args.no_key:
        import getpass
        try:
            entered = getpass.getpass("60db API key (input hidden, not echoed): ").strip()
        except (KeyboardInterrupt, EOFError):
            sys.exit("\naborted.")
        if entered:
            cfg["apiKey"] = entered
        elif "apiKey" not in cfg:
            sys.exit("ERROR: no key entered and none stored. Re-run init and paste your key.")
    if args.voice is not None:
        cfg["voice_id"] = args.voice
    if args.model is not None:
        cfg["model"] = args.model
    if args.output_format is not None:
        cfg["output_format"] = args.output_format
    if args.sample_rate is not None:
        cfg["sample_rate"] = args.sample_rate
    p = save_config(cfg)
    print(f"saved config -> {p}  (mode 600)")
    print("the key is stored locally only — it is never printed or committed.")


# ----------------------------------------------------------------------------- cli
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="sixtydb.py", description="60db.ai voice platform client")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="store API key (hidden) + defaults")
    pi.add_argument("--no-key", action="store_true", help="update defaults without touching the key")
    pi.add_argument("--voice", default=None, help="default voice id")
    pi.add_argument("--model", default=None, help="default model (e.g. 60db-quality)")
    pi.add_argument("--sample-rate", type=int, default=None, dest="sample_rate")
    pi.add_argument("--format", default=None, dest="output_format", help="default output format")

    sub.add_parser("doctor", help="diagnose setup")

    pv = sub.add_parser("voices", help="list voices")
    pv.add_argument("--mine", action="store_true", help="only your cloned voices")
    pv.add_argument("--json", action="store_true", dest="as_json")

    pl = sub.add_parser("langs", help="list supported languages")
    pl.add_argument("--stt", action="store_true", help="STT languages (default: TTS)")
    pl.add_argument("--json", action="store_true", dest="as_json")

    pt = sub.add_parser("tts", help="text -> WAV")
    pt.add_argument("text", help="text, or a path to a .txt file")
    pt.add_argument("--out", type=Path, default=Path("out/voiceover.wav"))
    pt.add_argument("--voice", default=None)
    pt.add_argument("--model", default=None)
    pt.add_argument("--sample-rate", type=int, default=None, dest="sample_rate")
    pt.add_argument("--speed", type=float, default=None, help="0.5-2.0")
    pt.add_argument("--stability", type=int, default=None, help="0-100 (REST)")
    pt.add_argument("--similarity", type=int, default=None, help="0-100 (REST)")
    pt.add_argument("--ws", action="store_true", help="legacy WebSocket stream (~8 kHz)")
    pt.add_argument("--no-enhance", action="store_true", help="disable enhance (REST)")

    ps = sub.add_parser("stt", help="audio -> transcript")
    ps.add_argument("audio", help="audio file (<=10 MB, <=1 hr)")
    ps.add_argument("--language", default=None, help="ISO 639-1 code, or omit for auto-detect")
    ps.add_argument("--diarize", action="store_true", help="speaker identification")
    ps.add_argument("--timestamps", action="store_true", help="word-level timings")
    ps.add_argument("--confidence", action="store_true", help="per-word confidence")
    ps.add_argument("--context", default=None, help="domain/speaker hints to boost accuracy")
    ps.add_argument("--out", default=None, help="write transcript text to a file")
    ps.add_argument("--json", action="store_true", dest="as_json")

    pc = sub.add_parser("clone", help="create a cloned voice (UNVERIFIED endpoint — test first)")
    pc.add_argument("--name", required=True)
    pc.add_argument("--sample", action="append", dest="samples",
                    help="audio file, repeatable (docs: 3-10 files, 10-60s each, >=2 min total)")
    pc.add_argument("--sample-url", default=None, dest="sample_url", help="single sample URL (alt input)")
    pc.add_argument("--description", default=None)
    pc.add_argument("--language", default=None)
    pc.add_argument("--gender", default=None, help="male / female / neutral")

    pd = sub.add_parser("delete-voice", help="delete one of your cloned voices (irreversible)")
    pd.add_argument("voice_id")

    pch = sub.add_parser("chat", help="one-shot LLM completion (voice-agent core)")
    pch.add_argument("message")
    pch.add_argument("--model", default=None, help="chat model (default 60db-tiny)")
    pch.add_argument("--system", default=None, help="system prompt")
    pch.add_argument("--chat-id", default=None, dest="chat_id", help="continue a saved conversation")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    cfg = load_config()

    if args.cmd == "init":
        cmd_init(args)
    elif args.cmd == "doctor":
        doctor()
    elif args.cmd == "voices":
        list_voices(args.mine, args.as_json)
    elif args.cmd == "langs":
        list_languages(args.stt, args.as_json)
    elif args.cmd == "tts":
        text = read_text_arg(args.text)
        voice = str(resolve("voice_id", args.voice, cfg) or "")
        rate = int(resolve("sample_rate", args.sample_rate, cfg) or DEFAULTS["sample_rate"])
        if args.ws:
            synth_ws(text, args.out, voice, rate)
        else:
            model = str(resolve("model", args.model, cfg) or "")
            speed = float(resolve("speed", args.speed, cfg) or DEFAULTS["speed"])
            stability = int(resolve("stability", args.stability, cfg) or DEFAULTS["stability"])
            similarity = int(resolve("similarity", args.similarity, cfg) or DEFAULTS["similarity"])
            enhance = bool(cfg.get("enhance", True)) and not args.no_enhance
            synth_rest(text, args.out, voice, rate, model, speed, stability, similarity, enhance)
    elif args.cmd == "stt":
        transcribe(args.audio, args.language, args.diarize, args.timestamps,
                   args.confidence, args.context, args.out, args.as_json)
    elif args.cmd == "clone":
        clone_voice(args.name, args.samples, args.description, args.language, args.gender, args.sample_url)
    elif args.cmd == "delete-voice":
        delete_voice(args.voice_id)
    elif args.cmd == "chat":
        chat(args.message, str(resolve("chat_model", args.model, cfg) or DEFAULTS["chat_model"]),
             args.system, args.chat_id)


if __name__ == "__main__":
    main()
