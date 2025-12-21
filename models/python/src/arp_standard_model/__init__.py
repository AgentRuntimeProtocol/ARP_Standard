from __future__ import annotations

__version__ = "0.2.0"
SPEC_REF = "spec/v1@v0.2.0"

try:
    from . import _generated as _generated
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError(
        "Generated models are missing. Run tools/codegen/python/model/generate.py"
    ) from exc

try:
    from . import _requests as _requests
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError(
        "Generated request models are missing. Run tools/codegen/python/model/generate.py"
    ) from exc

exports: dict[str, object] = {
    "__version__": __version__,
    "SPEC_REF": SPEC_REF,
}

if hasattr(_generated, "__all__"):
    for name in _generated.__all__:
        exports[name] = getattr(_generated, name)
else:
    for name, value in _generated.__dict__.items():
        if not name.startswith("_"):
            exports[name] = value

if hasattr(_requests, "__all__"):
    for name in _requests.__all__:
        exports[name] = getattr(_requests, name)
else:
    for name, value in _requests.__dict__.items():
        if not name.startswith("_"):
            exports[name] = value

__all__ = list(exports.keys())
globals().update(exports)
