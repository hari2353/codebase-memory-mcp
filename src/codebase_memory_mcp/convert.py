"""File converter (borrowed from DragShift's drag-and-drop converter idea).

Thin dispatch layer: PDF -> markdown (via the already-installed MinerU CLI),
plain text/markdown read-through, everything else unsupported. Keeps the
converter logic in one place so the MCP indexer and job-hunt pipeline share it.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


class UnsupportedFormat(Exception):
    pass


def pdf_to_text(pdf_path: str | Path, mineru_bin: str = "mineru") -> str:
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(str(pdf_path))
    proc = subprocess.run(
        [mineru_bin, "parse", str(pdf_path), "--tier", "flash"],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "mineru failed")
    return proc.stdout


def convert(path: str | Path, mineru_bin: str = "mineru") -> str:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        return pdf_to_text(p, mineru_bin=mineru_bin)
    if suffix in (".md", ".txt", ".rst"):
        return p.read_text(encoding="utf-8", errors="replace")
    raise UnsupportedFormat(f"no converter for {suffix or '(no extension)'}")

