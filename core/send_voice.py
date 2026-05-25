"""
雪的语音消息发送工具（GPT-SoVITS 版）
用法：python send_voice.py "消息文字\n[emotion: tender]" [chat_id]

text 末尾可附 [emotion: xxx] 标签（neutral/tender/playful/happy/sad/excited）。
标签会被解析后从合成文字中剥离，不发给对方。
依赖：需要预先启动 GPT-SoVITS API server（运行 start_voice_api.bat）
"""
import json
import os
import re
import sys
import tempfile
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = str(BASE_DIR / "config.json")


def _resolve(p):
    return str((BASE_DIR / p).resolve()) if p and not os.path.isabs(p) else p

VALID_EMOTIONS = {"neutral", "tender", "playful", "happy", "sad", "excited"}

def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)

def parse_emotion(text: str) -> tuple[str, str]:
    """从文字末尾解析并剥离 [emotion: xxx] 标签，返回 (clean_text, emotion)。"""
    match = re.search(r'\[emotion:\s*(\w+)\]\s*$', text.strip())
    if match:
        emotion = match.group(1).lower()
        if emotion not in VALID_EMOTIONS:
            emotion = "neutral"
        clean = text[:match.start()].strip()
        return clean, emotion
    return text.strip(), "neutral"

def check_server(base_url: str) -> bool:
    try:
        r = requests.get(base_url, timeout=3)
        return r.status_code < 500
    except Exception:
        return False

def set_models(base_url: str, cfg: dict):
    try:
        import urllib.parse
        requests.get(
            f"{base_url}/set_gpt_weights",
            params={"weights_path": cfg["gpt_model_path"]},
            timeout=30,
        )
        requests.get(
            f"{base_url}/set_sovits_weights",
            params={"weights_path": cfg["sovits_model_path"]},
            timeout=30,
        )
    except Exception as e:
        print(f"[warn] set_models: {e}", file=sys.stderr)

def synthesize(text: str, cfg: dict) -> bytes:
    base_url = cfg["gptsovits_api"]

    if not check_server(base_url):
        raise RuntimeError(
            f"GPT-SoVITS API server not running at {base_url}. "
            "Please start start_voice_api.bat first."
        )

    set_models(base_url, cfg)

    payload = {
        "text": text,
        "text_lang": "ja",
        "ref_audio_path": cfg["ref_audio_path"],
        "prompt_text": cfg["ref_text"],
        "prompt_lang": "ja",
        "media_type": "wav",
        "streaming_mode": False,
        "top_k": 5,
        "top_p": 1.0,
        "temperature": 1.0,
        "speed_factor": 1.0,
        "repetition_penalty": 1.35,
    }

    resp = requests.post(f"{base_url}/tts", json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"TTS failed HTTP {resp.status_code}: {resp.text[:300]}")

    return resp.content

def send_voice(raw_text: str, chat_id: str = None) -> dict:
    cfg = load_config()
    if chat_id is None:
        chat_id = cfg["default_chat_id"]

    text, emotion = parse_emotion(raw_text)
    print(f"[send_voice] text={text!r} emotion={emotion}", file=sys.stderr)

    cfg["gpt_model_path"] = _resolve(cfg["gpt_model_path"])
    cfg["sovits_model_path"] = _resolve(cfg["sovits_model_path"])
    cfg["ref_audio_path"] = _resolve(cfg["ref_audio_path"])

    audio_data = synthesize(text, cfg)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name

    try:
        url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendVoice"
        with open(tmp_path, "rb") as f:
            resp = requests.post(
                url,
                data={"chat_id": chat_id},
                files={"voice": ("voice.wav", f, "audio/wav")},
                timeout=30,
            )
        result = resp.json()
        result["_emotion"] = emotion
        return result
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python send_voice.py "text\\n[emotion: tender]" [chat_id]')
        sys.exit(1)
    raw = sys.argv[1].replace("\\n", "\n")
    chat_id = sys.argv[2] if len(sys.argv) > 2 else None
    result = send_voice(raw, chat_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
