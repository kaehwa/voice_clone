# app/router.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi import status
from typing import List, Optional, Union

import os
from pathlib import Path
from .schema import (
    ListVoicesQuery, VoiceOut, VoiceListResponse,
    CloneResponse,
    SynthesizeRequest, SynthesizeResponse,
    Message,
)
from .model import SpeechifyService, ApiError
from .utils import resolve_api_key

router = APIRouter(prefix="/tts", tags=["TTS"])
# Default clone settings (user need only provide sample audio and text)
CONSENT_NAME = os.getenv("CONSENT_NAME", "전정웅")
CONSENT_EMAIL = os.getenv("CONSENT_EMAIL", "jj7141@gmail.com")
CLONE_NAME = os.getenv("CLONE_NAME", "my-ko-clone")
CLONE_LOCALE = os.getenv("CLONE_LOCALE", "ko-KR")
CLONE_GENDER = os.getenv("CLONE_GENDER", "notSpecified")
LOCAL_HOST = os.getenv("LOCALHOST", "http://localhost:8000")
def get_service() -> SpeechifyService:
    token = resolve_api_key()
    return SpeechifyService(token=token)

@router.get("/health", response_model=Message)
def health():
    return {"message": "ok"}

# --- Voices ---
'''
    1) 메세지 (카드 메세지)
    2) 대상 음성 (a)
    dict = {
        Flower
        id	integer($int64)
        flowerFrom	""
        flowerTo	""
        relation	""
        anniversary	""
        anvDate	""
        history	""
        cardImage	""
        cardVoice	정웅이가 만든 .wav파일의 byte 형태 (blob)
        recommendMessage	""
    }

'''
@router.post("/voices", response_model=VoiceListResponse)
def list_voices(
    #card_msg  : Optional[str] = None,
    #voice_file : Optional[str] = None,
    locale: Optional[str] = None,
    name_like: Optional[str] = None,
    include_personal: bool = False,
    svc: SpeechifyService = Depends(get_service),
):

    try:
        raw = svc.list_voices_raw()
        filtered = svc.filter_voices(raw, locale, name_like, include_personal)
        voices: List[VoiceOut] = [
            VoiceOut(
                id=str(v.id) if hasattr(v, "id") else str(v.get("id")),
                display_name=str(getattr(v, "display_name", None) or v.get("display_name")),
                locale=str(getattr(v, "locale", None) or v.get("locale")),
                type=str(getattr(v, "type", None) or v.get("type")),
            )
            for v in filtered
        ]
        return {"voices": voices}
    except ApiError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.body or "Speechify API error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Clone & Optional Synthesize ---
@router.post(
    "/clone",
    response_model=Union[CloneResponse, SynthesizeResponse],
    status_code=status.HTTP_201_CREATED,
)
async def clone_and_synthesize(
    sample: UploadFile = File(..., description="클론용 WAV 파일"),
    text: Optional[str] = Form(None, description="합성할 텍스트 (클론 후 합성을 원할 경우)"),
    svc: SpeechifyService = Depends(get_service),
):
    try:
        # 임시 저장
        content = await sample.read()
        tmp = Path("outputs") / f"_tmp_{sample.filename}"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(content)
        # 클론 생성
        voice_id = svc.create_clone(
            sample_path=tmp,
            name=CLONE_NAME,
            locale=CLONE_LOCALE,
            gender=CLONE_GENDER,
            full_name=CONSENT_NAME,
            email=CONSENT_EMAIL,
        )
        tmp.unlink(missing_ok=True)
        # 텍스트 미제공 시 클론 ID 반환
        if not text:
            return {"voice_id": voice_id}
        # 텍스트 제공 시 합성 수행
        out_path = svc.synthesize_to_file(
            text=text,
            voice_id=voice_id,
        )
        return {"file_url": f"{LOCAL_HOST}/static/{out_path.name}", "filename": out_path.name}
    except ApiError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.body or "Speechify API error")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Synthesize ---
@router.post("/synthesize", response_model=SynthesizeResponse)
def synthesize(req: SynthesizeRequest, svc: SpeechifyService = Depends(get_service)):
    try:
        out_path = svc.synthesize_to_file(
            text=req.text,
            voice_id=req.voice_id,
            lang=req.lang,
            model=req.model,
            audio_format=req.format,
            emotion=req.emotion,
            rate=req.rate,
            pitch=req.pitch,
            break_ms=req.break_ms,
        )
        # /static 에 마운트된 정적 파일 URL 반환
        filename = out_path.name
        return {
            "file_url": f"{LOCAL_HOST}/{filename}",
            "filename": filename,
        }
    except ApiError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.body or "Speechify API error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))