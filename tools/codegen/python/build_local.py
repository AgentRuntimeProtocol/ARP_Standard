#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
import shutil
import zipfile
from pathlib import Path


def _require_module(module: str, *, install_hint: str) -> None:
    try:
        __import__(module)
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(f"Missing dependency: {module}. Install with: {install_hint}") from exc


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(cmd, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1alpha2", help="Spec version directory (default: v1alpha2)")
    parser.add_argument("--clean", action="store_true", help="Remove existing dist/ before building")
    parser.add_argument("--list-wheel", action="store_true", help="List wheel contents after build")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    sdk_root = repo_root / "sdks" / "python"
    dist_dir = sdk_root / "dist"

    install_hint = "python -m pip install -r tools/codegen/python/requirements-dev.txt"
    _require_module("ruamel.yaml", install_hint=install_hint)
    _require_module("build", install_hint=install_hint)
    _require_module("twine", install_hint=install_hint)

    generator_exe = Path(sys.executable).parent / "openapi-python-client"
    if not generator_exe.exists():
        raise SystemExit(f"Missing openapi-python-client executable. Install with: {install_hint}")

    _run([sys.executable, "tools/codegen/python/generate.py", "--version", args.version], cwd=repo_root)

    if args.clean and dist_dir.exists():
        for path in dist_dir.iterdir():
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)

    _run([sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", "dist"], cwd=sdk_root)

    dists = sorted(dist_dir.glob("*"))
    if not dists:
        raise SystemExit(f"No artifacts found in {dist_dir}")

    _run([sys.executable, "-m", "twine", "check", *[str(p) for p in dists]], cwd=sdk_root)

    print("Built artifacts:")
    for path in dists:
        print(f"- {path.relative_to(repo_root)}")

    if args.list_wheel:
        wheel = next((p for p in dists if p.suffix == ".whl"), None)
        if wheel is not None:
            print(f"\nWheel contents ({wheel.name}):")
            with zipfile.ZipFile(wheel) as zf:
                for name in sorted(zf.namelist()):
                    print(name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
