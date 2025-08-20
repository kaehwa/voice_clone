# app/schema.py
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

# --- 공통 ---
class Message(BaseModel):
    message: str

# --- 보이스 목록 ---
class VoiceOut(BaseModel):
    id: str
    display_name: Optional[str] = None
    locale: Optional[str] = None
    type: Optional[str] = None

class ListVoicesQuery(BaseModel):
    locale: Optional[str] = Field(default=None, description="예: ko-KR")
    name_like: Optional[str] = Field(default=None, description="표시명 부분 일치 필터")
    include_personal: bool = Field(default=False, description="개인 클론 보이스 포함 여부")

class VoiceListResponse(BaseModel):
    voices: List[VoiceOut]
    # id: str
    # flowerFrom: str
    # flowerTo: str
    # relation: str
    # anniversary: str
    # anvDate: str
    # history: str
    # cardImage: str
    # cardVoice: str
    # recommendMessage: str
    

# --- 클론 생성 ---
Gender = Literal["male", "female", "notSpecified"]

class CloneResponse(BaseModel):
    voice_id: str

# --- 합성 ---
class SynthesizeRequest(BaseModel):
    text: str = Field(..., description="플레인 텍스트 또는 자동 SSML 래핑 전 텍스트")
    voice_id: str = Field(..., description="합성에 사용할 보이스 ID")
    lang: str = Field(default="ko-KR")
    model: str = Field(default="simba-multilingual")
    format: Literal["mp3", "wav", "ogg", "aac"] = Field(default="mp3")

    # 선택적 감정/프로소디
    emotion: Optional[str] = Field(default=None, description="예: warm, excited, calm")
    rate: Optional[str] = Field(default=None, description="예: slow, fast, 90%, 120%")
    pitch: Optional[str] = Field(default=None, description="예: low, high, -2st, +2st")
    break_ms: Optional[int] = Field(default=None, description="문장 뒤 쉬는 시간(ms)")

class SynthesizeResponse(BaseModel):
    file_url: str
    filename: str