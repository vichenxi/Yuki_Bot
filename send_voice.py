"""
雪的语音消息发送工具（GPT-SoVITS 版）
用法：python send_voice.py "消息文字[emotion: tender]" [chat_id]

emotion 可选：neutral/tender/playful/happy/sad/excited
依赖：需要预先启动 GPT-SoVITS API server（start_voice_api.bat）
"""
import json, os, re, sys, tempfile
import urllib.request, urllib.parse, urllib.error

BASE        = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
VALID_EMOTIONS = {"neutral", "tender", "playful", "happy", "sad", "excited"}


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def parse_emotion(text: str):
    m = re.search(r'\[emotion:\s*(\w+)\]\s*$', text.strip())
    if m:
        emotion = m.group(1).lower()
        if emotion not in VALID_EMOTIONS:
            emotion = "neutral"
        return text[:m.start()].strip(), emotion
    return text.strip(), "neutral"


def check_server(base_url: str) -> bool:
    try:
        urllib.request.urlopen(base_url, timeout=3)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def set_models(base_url: str, cfg: dict):
    for endpoint, key in [("set_gpt_weights", "gpt_model_path"),
                           ("set_sovits_weights", "sovits_model_path")]:
        try:
            url = f"{base_url}/{endpoint}?weights_path={urllib.parse.quote(cfg[key], safe='')}"
            urllib.request.urlopen(url, timeout=30)
        except Exception as e:
            print(f"[warn] {endpoint}: {e}", file=sys.stderr)


def synthesize(text: str, cfg: dict) -> bytes:
    base_url = cfg["gptsovits_api"]
    if not check_server(base_url):
        raise RuntimeError(f"GPT-SoVITS API 未运行：{base_url}")
    set_models(base_url, cfg)
    lang = cfg.get("voice_lang", "zh")
    payload = json.dumps({
        "text": text,
        "text_lang": lang,
        "ref_audio_path": cfg["ref_audio_path"],
        "prompt_text": cfg["ref_text"],
        "prompt_lang": lang,
        "media_type": "wav",
        "streaming_mode": False,
        "top_k": 5, "top_p": 1.0, "temperature": 1.0,
        "speed_factor": 1.0, "repetition_penalty": 1.35,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/tts", data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def send_voice(raw_text: str, chat_id: str = None) -> dict:
    cfg = load_config()
    if chat_id is None:
        chat_id = str(cfg["default_chat_id"])
    text, emotion = parse_emotion(raw_text)
    print(f"[send_voice] text={text!r} emotion={emotion}", file=sys.stderr)
    audio_data = synthesize(text, cfg)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name
    try:
        boundary = "yuki_voice_bdry"
        body = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n"
        ).encode()
        with open(tmp_path, "rb") as f:
            body += (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"voice\"; filename=\"voice.wav\"\r\n"
                f"Content-Type: audio/wav\r\n\r\n"
            ).encode() + f.read() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{cfg['bot_token']}/sendVoice",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
        result["_emotion"] = emotion
        return result
    finally:
        try: os.unlink(tmp_path)
        except Exception: pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python send_voice.py "text[emotion: tender]" [chat_id]')
        sys.exit(1)
    raw  = sys.argv[1].replace("\\n", "\n")
    cid  = sys.argv[2] if len(sys.argv) > 2 else None
    result = send_voice(raw, cid)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result.get("ok") else 1)
