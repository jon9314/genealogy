from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence

from pypdf import PdfReader

from .settings import get_settings


class OCRProcessError(RuntimeError):
    pass


def run_ocr(source_pdf: Path, output_pdf: Path) -> list[str]:
    """Run ocrmypdf and return extracted text per page."""
    settings = get_settings()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    cmd: list[str] = [
        settings.ocrmypdf_executable,
        "--optimize",
        "3",
        "--deskew",
        "--rotate-pages",
        "--rotate-pages-threshold",
        "12",
        "--output-type",
        "pdfa",
        "--fast-webview",
        "0",
        "-l",
        settings.ocrmypdf_language,
    ]
    if settings.ocrmypdf_remove_background:
        cmd.append("--remove-background")
    cmd.extend([str(source_pdf), str(output_pdf)])
    try:
        subprocess.run(
            cmd,
            check=True,
            timeout=settings.ocrmypdf_timeout_secs,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - subprocess error
        raise OCRProcessError(f"OCR command failed with exit code {exc.returncode}") from exc
    except subprocess.TimeoutExpired as exc:  # pragma: no cover
        raise OCRProcessError("OCR command timed out") from exc

    reader = PdfReader(str(output_pdf))
    texts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        texts.append(text)
    return texts
