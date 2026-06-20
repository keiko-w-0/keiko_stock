#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.iwencai_recall import bge_device_name, bge_model_name, ensure_local_bge_model, get_bge_embedder, local_bge_model_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the local BGE model for iWenCai recall.")
    parser.add_argument("--model", default="", help="Override IWENCAI_BGE_MODEL.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    model_name = args.model.strip() or bge_model_name()
    try:
        model_path = ensure_local_bge_model(model_name)
        embedder = get_bge_embedder(model_name)
        vector_size = len(embedder.encode_query("先进封装"))
        payload = {
            "status": "ok",
            "model": model_name,
            "path": str(model_path),
            "device": bge_device_name(),
            "vector_size": vector_size,
            "ready": model_path.exists() and (model_path / "config.json").exists(),
        }
    except Exception as exc:  # noqa: BLE001 - CLI should surface actionable errors.
        payload = {
            "status": "failed",
            "model": model_name,
            "path": str(local_bge_model_dir(model_name)),
            "error": str(exc),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"model={payload['model']}")
        print(f"path={payload['path']}")
        print(f"device={payload['device']}")
        print(f"vector_size={payload['vector_size']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
