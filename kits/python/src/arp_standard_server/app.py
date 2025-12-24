from __future__ import annotations

from fastapi import APIRouter, FastAPI

from . import __version__
from .auth import AuthSettings, register_auth_middleware
from .errors import register_exception_handlers


def build_app(
    *,
    router: APIRouter,
    title: str,
    auth_settings: AuthSettings | None = None,
) -> FastAPI:
    app = FastAPI(title=title, version=__version__)

    app.include_router(router)
    register_exception_handlers(app)
    settings = AuthSettings.from_env() if auth_settings is None else auth_settings
    register_auth_middleware(app, settings=settings)
    return app
