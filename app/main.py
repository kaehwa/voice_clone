# app/main.py
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from .router import router as tts_router
from .utils import ensure_output_dir

def create_app() -> FastAPI:
    app = FastAPI(title="VoiceClone FastAPI", version="1.0.0")

    # CORS (필요 시 허용 도메인 조정)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    # 정적 파일 마운트 (합성된 오디오 제공)
    ensure_output_dir()
    app.mount("/static", StaticFiles(directory="outputs"), name="static")

    # 라우터 등록
    app.include_router(tts_router)

    @app.get("/", tags=["root"])
    def root():
        return {"message": "Speechify TTS API. See /docs"}

    return app

app = create_app()
