# app/__init__.py
"""
'app' 패키지 초기화.
필요 시 외부에서 `from app import app, create_app` 형태로 사용할 수 있도록 재노출합니다.
부작용을 최소화하기 위해 로직은 넣지 않습니다.
"""

from .main import create_app, app  # noqa: F401

__all__ = ["create_app", "app"]
