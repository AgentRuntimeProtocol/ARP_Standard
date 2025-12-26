from __future__ import annotations

__version__ = "0.3.0"
SPEC_REF = "spec/v1@v0.3.0"

try:
    from ._generated import *  # noqa: F403
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError(
        "Generated models are missing. Run tools/codegen/python/model/generate.py"
    ) from exc

try:
    from ._requests import *  # noqa: F403
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError(
        "Generated request models are missing. Run tools/codegen/python/model/generate.py"
    ) from exc

__all__ = ["__version__", "SPEC_REF"]  # pyright: ignore[reportUnsupportedDunderAll]
for name in list(globals()):
    if name.startswith("_") or name in __all__:
        continue
    __all__.append(name)  # pyright: ignore[reportUnsupportedDunderAll]
