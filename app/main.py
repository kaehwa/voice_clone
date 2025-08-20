# app/main.py
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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

    # Custom handler for validation errors -> 400 Bad Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from fastapi import Request

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Aggregate validation error messages
        msgs = [err.get("msg") for err in exc.errors()]
        return JSONResponse(status_code=400, content={"message": "\n".join(msgs)})

    # Override HTTPException for status 400 to use Message schema
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code == 400:
            return JSONResponse(status_code=400, content={"message": exc.detail or "Bad Request"})
        # fallback to default handler
        raise exc

    @app.get("/", tags=["root"])
    def root():
        return {"message": "Speechify TTS API. See /docs"}

    return app

app = create_app()
