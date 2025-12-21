from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI

from . import __version__
from .auth import api_key_dependency
from .errors import register_exception_handlers


def build_app(
    *,
    router: APIRouter,
    title: str,
    api_key: str | None = None,
    api_key_header: str = "X-API-Key",
) -> FastAPI:
    app = FastAPI(title=title, version=__version__)

    if api_key:
        dependency = api_key_dependency(api_key, header_name=api_key_header)
        app.include_router(router, dependencies=[Depends(dependency)])
    else:
        app.include_router(router)

    register_exception_handlers(app)
    return app
