from __future__ import annotations

__all__ = ["__version__", "SPEC_REF", "ArpServerError"]

__version__ = "0.2.1"
SPEC_REF = "spec/v1@v0.2.1"

from .errors import ArpServerError  # noqa: E402
