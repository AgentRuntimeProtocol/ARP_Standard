#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
import tomllib
import zipfile
from pathlib import Path


def _read_version(pyproject_path: Path) -> str:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return data["project"]["version"]


def _read_spec_ref(init_path: Path) -> str:
    text = init_path.read_text(encoding="utf-8")
    match = re.search(r"^SPEC_REF\s*=\s*[\"']([^\"']+)[\"']\s*$", text, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Missing SPEC_REF in {init_path}")
    return match.group(1)


def _wheel_metadata(wheel_path: Path) -> list[str]:
    with zipfile.ZipFile(wheel_path) as zf:
        metadata_files = [name for name in zf.namelist() if name.endswith(".dist-info/METADATA")]
        if not metadata_files:
            raise RuntimeError(f"Missing METADATA in {wheel_path}")
        content = zf.read(metadata_files[0]).decode("utf-8")
    return content.splitlines()


def _find_wheels(dist_dir: Path) -> list[Path]:
    return sorted(dist_dir.glob("*.whl"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1", help="Spec version directory (default: v1)")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    model_root = repo_root / "models" / "python"
    client_root = repo_root / "clients" / "python"
    server_root = repo_root / "kits" / "python"
    conformance_root = repo_root / "conformance" / "python"

    model_version = _read_version(model_root / "pyproject.toml")
    client_version = _read_version(client_root / "pyproject.toml")
    server_version = _read_version(server_root / "pyproject.toml")
    conformance_version = _read_version(conformance_root / "pyproject.toml")
    if model_version != client_version or model_version != server_version or model_version != conformance_version:
        print(
            "Version mismatch: "
            f"model={model_version} client={client_version} server={server_version} conformance={conformance_version}",
            file=sys.stderr,
        )
        return 1

    expected_spec_ref = f"spec/{args.version}@v{model_version}"
    model_spec_ref = _read_spec_ref(model_root / "src" / "arp_standard_model" / "__init__.py")
    client_spec_ref = _read_spec_ref(client_root / "src" / "arp_standard_client" / "__init__.py")
    server_spec_ref = _read_spec_ref(server_root / "src" / "arp_standard_server" / "__init__.py")
    conformance_spec_ref = _read_spec_ref(conformance_root / "src" / "arp_conformance" / "__init__.py")
    for name, value in [
        ("model", model_spec_ref),
        ("client", client_spec_ref),
        ("server", server_spec_ref),
        ("conformance", conformance_spec_ref),
    ]:
        if value != expected_spec_ref:
            print(f"{name} SPEC_REF mismatch: {value} (expected {expected_spec_ref})", file=sys.stderr)
            return 1

    model_wheels = _find_wheels(model_root / "dist")
    client_wheels = _find_wheels(client_root / "dist")
    server_wheels = _find_wheels(server_root / "dist")
    conformance_wheels = _find_wheels(conformance_root / "dist")
    if not model_wheels:
        print("Missing model wheel in models/python/dist", file=sys.stderr)
        return 1
    if not client_wheels:
        print("Missing client wheel in clients/python/dist", file=sys.stderr)
        return 1
    if not server_wheels:
        print("Missing server wheel in kits/python/dist", file=sys.stderr)
        return 1
    if not conformance_wheels:
        print("Missing conformance wheel in conformance/python/dist", file=sys.stderr)
        return 1

    model_match = any(re.search(rf"{re.escape(model_version)}", wheel.name) for wheel in model_wheels)
    client_match = any(re.search(rf"{re.escape(client_version)}", wheel.name) for wheel in client_wheels)
    server_match = any(re.search(rf"{re.escape(server_version)}", wheel.name) for wheel in server_wheels)
    conformance_match = any(re.search(rf"{re.escape(conformance_version)}", wheel.name) for wheel in conformance_wheels)
    if not model_match:
        print(f"No model wheel matches version {model_version}", file=sys.stderr)
        return 1
    if not client_match:
        print(f"No client wheel matches version {client_version}", file=sys.stderr)
        return 1
    if not server_match:
        print(f"No server wheel matches version {server_version}", file=sys.stderr)
        return 1
    if not conformance_match:
        print(f"No conformance wheel matches version {conformance_version}", file=sys.stderr)
        return 1

    required = f"arp-standard-model=={model_version}"
    missing_client = True
    for wheel in client_wheels:
        lines = _wheel_metadata(wheel)
        if any(line.strip() == f"Requires-Dist: {required}" for line in lines):
            missing_client = False
            break
    if missing_client:
        print(f"Client wheel missing dependency: {required}", file=sys.stderr)
        return 1
    missing_server = True
    for wheel in server_wheels:
        lines = _wheel_metadata(wheel)
        if any(line.strip() == f"Requires-Dist: {required}" for line in lines):
            missing_server = False
            break
    if missing_server:
        print(f"Server wheel missing dependency: {required}", file=sys.stderr)
        return 1

    forbidden = {"arp-standard-model", "arp-standard-client", "arp-standard-server"}
    for wheel in conformance_wheels:
        lines = _wheel_metadata(wheel)
        for line in lines:
            if not line.startswith("Requires-Dist:"):
                continue
            req = line.split(":", 1)[1].strip()
            name = re.split(r"[ ;(<=>]", req, maxsplit=1)[0].strip()
            if name in forbidden:
                print(f"Conformance wheel has forbidden dependency: {req}", file=sys.stderr)
                return 1

    print("OK: dist dependencies verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
