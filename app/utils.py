# app/utils.py
import os
import base64
import json
from pathlib import Path
from typing import Any, Optional

# Speechify SDK & ApiError 안전 임포트
from speechify import Speechify
try:
    from speechify.core.api_error import ApiError
except Exception:
    class ApiError(Exception):
        def __init__(self, status_code=None, body=None, *a, **kw):
            super().__init__(body or "ApiError")
            self.status_code = status_code
            self.body = body

OUTPUT_DIR = Path("outputs")

def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR

def get_field(obj: Any, key: str, default=None):
    """speechify SDK 응답 객체/딕트/데이터클래스에서 안전하게 필드 조회"""
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key, default)
    if hasattr(obj, "to_dict"):
        try:
            d = obj.to_dict()
            if isinstance(d, dict):
                return d.get(key, default)
        except Exception:
            pass
    return default

def resolve_api_key(cli_key: Optional[str] = None) -> str:
    if cli_key:
        return cli_key
    env_key = os.getenv("SPEECHIFY_API_KEY") or os.getenv("API_KEY")
    if env_key:
        return env_key
    raise RuntimeError("Speechify API key is required. Set SPEECHIFY_API_KEY or API_KEY.")

def wrap_emotion_ssml(
    text: str,
    emotion: Optional[str] = None,
    rate: Optional[str] = None,
    pitch: Optional[str] = None,
    break_ms: Optional[int] = None,
) -> str:
    """감정/속도/피치/쉼표를 간단히 SSML로 감싸기"""
    if not emotion and not rate and not pitch and not break_ms:
        return text  # SSML 불필요

    core = text
    if rate or pitch:
        r_attr = f' rate="{rate}"' if rate else ""
        p_attr = f' pitch="{pitch}"' if pitch else ""
        core = f"<prosody{r_attr}{p_attr}>{core}</prosody>"

    if emotion:
        core = f'<speechify:style emotion="{emotion}">{core}</speechify:style>'

    if break_ms and break_ms > 0:
        core = f'{core}<break time="{int(break_ms)}ms"/>'

    return f"<speak>{core}</speak>"

def write_b64_audio_to_file(audio_b64: str, out_path: Path) -> Path:
    out_path.write_bytes(base64.b64decode(audio_b64))
    return out_path