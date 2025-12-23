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
    parser.add_argument("--version", default="v1", help="Spec version directory (default: v1)")
    parser.add_argument("--clean", action="store_true", help="Remove existing dist/ before building")
    parser.add_argument("--list-wheel", action="store_true", help="List wheel contents after build")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    model_root = repo_root / "models" / "python"
    client_root = repo_root / "clients" / "python"
    server_root = repo_root / "kits" / "python"
    conformance_root = repo_root / "conformance" / "python"
    model_dist_dir = model_root / "dist"
    client_dist_dir = client_root / "dist"
    server_dist_dir = server_root / "dist"
    conformance_dist_dir = conformance_root / "dist"

    install_hint = (
        "python -m pip install -r tools/codegen/python/client/requirements-dev.txt "
        "-r tools/codegen/python/model/requirements.txt "
        "-r tools/codegen/python/server/requirements.txt "
        "-r tools/validate/requirements.txt"
    )
    _require_module("ruamel.yaml", install_hint=install_hint)
    _require_module("build", install_hint=install_hint)
    _require_module("twine", install_hint=install_hint)
    _require_module("datamodel_code_generator", install_hint=install_hint)

    generator_exe = Path(sys.executable).parent / "openapi-python-client"
    if not generator_exe.exists():
        raise SystemExit(f"Missing openapi-python-client executable. Install with: {install_hint}")

    _run([sys.executable, "tools/validate/validate_openapi.py", "--version", args.version], cwd=repo_root)
    _run([sys.executable, "tools/codegen/python/model/generate.py", "--version", args.version], cwd=repo_root)
    _run([sys.executable, "tools/codegen/python/client/generate.py", "--version", args.version], cwd=repo_root)
    _run([sys.executable, "tools/codegen/python/server/generate.py", "--version", args.version], cwd=repo_root)
    _run([sys.executable, "tools/conformance/sync_spec.py", "--version", args.version], cwd=repo_root)

    if args.clean:
        for target in (model_dist_dir, client_dist_dir, server_dist_dir, conformance_dist_dir):
            if not target.exists():
                continue
            for path in target.iterdir():
                if path.is_file():
                    path.unlink()
                else:
                    shutil.rmtree(path)

    _run([sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", "dist"], cwd=model_root)
    _run([sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", "dist"], cwd=client_root)
    _run([sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", "dist"], cwd=server_root)
    _run([sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", "dist"], cwd=conformance_root)

    model_dists = sorted(model_dist_dir.glob("*"))
    client_dists = sorted(client_dist_dir.glob("*"))
    server_dists = sorted(server_dist_dir.glob("*"))
    conformance_dists = sorted(conformance_dist_dir.glob("*"))
    if not model_dists:
        raise SystemExit(f"No artifacts found in {model_dist_dir}")
    if not client_dists:
        raise SystemExit(f"No artifacts found in {client_dist_dir}")
    if not server_dists:
        raise SystemExit(f"No artifacts found in {server_dist_dir}")
    if not conformance_dists:
        raise SystemExit(f"No artifacts found in {conformance_dist_dir}")

    _run([sys.executable, "-m", "twine", "check", *[str(p) for p in model_dists]], cwd=model_root)
    _run([sys.executable, "-m", "twine", "check", *[str(p) for p in client_dists]], cwd=client_root)
    _run([sys.executable, "-m", "twine", "check", *[str(p) for p in server_dists]], cwd=server_root)
    _run([sys.executable, "-m", "twine", "check", *[str(p) for p in conformance_dists]], cwd=conformance_root)

    print("Built artifacts:")
    for path in [*model_dists, *client_dists, *server_dists, *conformance_dists]:
        print(f"- {path.relative_to(repo_root)}")

    if args.list_wheel:
        for wheel in [*model_dists, *client_dists, *server_dists, *conformance_dists]:
            if wheel.suffix != ".whl":
                continue
            print(f"\nWheel contents ({wheel.name}):")
            with zipfile.ZipFile(wheel) as zf:
                for name in sorted(zf.namelist()):
                    print(name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
