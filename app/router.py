# app/router.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi import status
from typing import List, Optional

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
    print(f"[START] Listing voices")
    print(f"[DEBUG] locale => {locale}")
    try:
        # consent_name, consent_email = 상수로 선언하고 
        #1. voice file : str => .wav 저장 -> filepath
        #2. text(message) : str => 변수에 저장
        #3. 음성처리 함수에 전달  [리턴] = function(filepath, message, name, email)
        #4. voice_output -> byte형태로 변환
        #5. 지은이가 원하는 포맷으로 reponse 보냄
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

# --- Clone (multipart/form-data + 파일 업로드) ---
@router.post(
    "/clone",
    response_model=CloneResponse,
    status_code=status.HTTP_201_CREATED,
)
async def clone_voice(
    sample: UploadFile = File(..., description="클론용 WAV 파일"),
    svc: SpeechifyService = Depends(get_service),
):
    try:
        # 업로드 파일을 임시 저장
        content = await sample.read()
        tmp_path = Path("voice_output") / f"_tmp_{sample.filename}"
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_bytes(content)

        voice_id = svc.create_clone(
            sample_path=tmp_path,
            name=CLONE_NAME,
            locale=CLONE_LOCALE,
            gender=CLONE_GENDER,
            full_name=CONSENT_NAME,
            email=CONSENT_EMAIL,
        )
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        return {"voice_id": voice_id}
    except ApiError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.body or "Speechify API error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/clone-synthesize",
    response_model=SynthesizeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def clone_and_synthesize(
    sample: UploadFile = File(..., description="클론용 WAV 파일"),
    text: str = Form(..., description="합성할 텍스트"),
    lang: str = Form("ko-KR"),
    model: str = Form("simba-multilingual"),
    audio_format: str = Form("mp3"),
    emotion: Optional[str] = Form(None),
    rate: Optional[str] = Form(None),
    pitch: Optional[str] = Form(None),
    break_ms: Optional[int] = Form(None),
    svc: SpeechifyService = Depends(get_service),
):
    try:
        # 임시 저장 및 클론 생성
        content = await sample.read()
        tmp_path = Path("outputs") / f"_tmp_{sample.filename}"
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_bytes(content)
        voice_id = svc.create_clone(
            sample_path=tmp_path,
            name=CLONE_NAME,
            locale=CLONE_LOCALE,
            gender=CLONE_GENDER,
            full_name=CONSENT_NAME,
            email=CONSENT_EMAIL,
        )
        # 음성 합성
        out_path = svc.synthesize_to_file(
            text=text,
            voice_id=voice_id,
            lang=lang,
            model=model,
            audio_format=audio_format,
            emotion=emotion,
            rate=rate,
            pitch=pitch,
            break_ms=break_ms,
        )
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        # Prepare response URL
        filename = out_path.name
        return {"file_url": f"{LOCAL_HOST}/{filename}", "filename": filename}
    except ApiError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.body or "Speechify API error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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