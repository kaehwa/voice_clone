# app/model.py
import json
from pathlib import Path
from typing import Any, List, Optional

from speechify import Speechify
from .utils import (
    get_field,
    write_b64_audio_to_file,
    wrap_emotion_ssml,
    ensure_output_dir,
)
try:
    from speechify.core.api_error import ApiError
except Exception:
    class ApiError(Exception):
        def __init__(self, status_code=None, body=None, *a, **kw):
            super().__init__(body or "ApiError")
            self.status_code = status_code
            self.body = body

class SpeechifyService:
    """Speechify SDK thin wrapper"""

    def __init__(self, token: str):
        self.client = Speechify(token=token)

    # --- Voices ---
    def list_voices_raw(self) -> List[Any]:
        return self.client.tts.voices.list()

    def filter_voices(self, voices: List[Any], locale: Optional[str], name_like: Optional[str], include_personal: bool) -> List[Any]:
        out = []
        for v in voices:
            vtype = (get_field(v, "type") or "").lower()   # 'shared' | 'personal' | 'ai' 등
            if not include_personal and vtype == "personal":
                continue
            if locale and (get_field(v, "locale") or "").lower() != locale.lower():
                continue
            if name_like and name_like.lower() not in (get_field(v, "display_name") or "").lower():
                continue
            out.append(v)
        return out

    # --- Clone ---
    def create_clone(
        self,
        sample_path: Path,
        name: str,
        locale: str,
        gender: str,
        full_name: str,
        email: str,
    ) -> str:
        with sample_path.open("rb") as f:
            v = self.client.tts.voices.create(
                name=name,
                gender=gender,
                locale=locale,
                consent=json.dumps({"fullName": full_name, "email": email}),
                sample=f,
            )
        vid = get_field(v, "id")
        if not vid:
            raise RuntimeError(f"클론 응답에서 voice_id를 찾지 못했습니다: {type(v)}")
        return vid

    # --- TTS ---
    def synthesize_to_file(
        self,
        *,
        text: str,
        voice_id: str,
        lang: str = "ko-KR",
        model: str = "simba-multilingual",
        audio_format: str = "mp3",
        emotion: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        break_ms: Optional[int] = None,
    ) -> Path:
        # 텍스트 또는 SSML 래핑
        text_or_ssml = wrap_emotion_ssml(text, emotion, rate, pitch, break_ms)

        # API 호출
        res = self.client.tts.audio.speech(
            input=text_or_ssml,
            voice_id=voice_id,
            audio_format=audio_format,
            language=lang,
            model=model,
        )
        audio_b64 = get_field(res, "audio_data")
        if not audio_b64:
            raise RuntimeError("audio_data가 응답에 없습니다.")

        # 출력 디렉토리 생성 및 파일 저장
        out_dir = ensure_output_dir()
        safe_vid = voice_id[:12].replace("/", "_")
        filename = f"{safe_vid}_{abs(hash(text_or_ssml)) % (10**8)}.{audio_format}"
        out_path = out_dir / filename
        return write_b64_audio_to_file(audio_b64, out_path)