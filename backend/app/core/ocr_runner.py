from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import List

from pypdf import PdfReader

from .settings import Settings, get_settings


LOGGER = logging.getLogger(__name__)


class OCRProcessError(RuntimeError):
    """Raised when the OCR subprocess exits unsuccessfully."""


def build_ocr_cmd(input_pdf: Path, output_pdf: Path, settings: Settings) -> list[str]:
    """Construct the ocrmypdf command with optional tuning flags."""

    cmd: List[str] = [
        settings.ocrmypdf_executable,
        "--rotate-pages",
        "--rotate-pages-threshold",
        "12",
        "--deskew",
        "--optimize",
        "2",
        "--output-type",
        "pdf",
    ]

    if settings.remove_background:
        cmd.append("--remove-background")

    fast_web_view_mb = settings.fast_web_view_mb
    if isinstance(fast_web_view_mb, int) and fast_web_view_mb > 0:
        cmd.extend(["--fast-web-view", str(fast_web_view_mb)])

    if settings.language:
        cmd.extend(["-l", settings.language])

    cmd.extend([str(input_pdf), str(output_pdf)])
    return cmd


def run_ocr(source_pdf: Path, output_pdf: Path) -> list[str]:
    """Run ocrmypdf and return extracted text per page."""

    settings = get_settings()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_ocr_cmd(source_pdf, output_pdf, settings)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.ocrmypdf_timeout_secs,
        )
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - subprocess timeout
        LOGGER.error(
            "OCR command timed out after %s seconds", settings.ocrmypdf_timeout_secs
        )
        raise OCRProcessError("OCR command timed out") from exc

    if result.returncode != 0:  # pragma: no cover - subprocess failure
        stderr = (result.stderr or "").strip()
        tail = "\n".join(stderr.splitlines()[-5:]) if stderr else ""
        LOGGER.error(
            "OCR command failed (exit %s): %s",
            result.returncode,
            tail or "no stderr output",
        )
        raise OCRProcessError(
            f"OCR failed (exit {result.returncode}): {tail or 'see logs'}"
        )

    reader = PdfReader(str(output_pdf))
    texts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        texts.append(text)
    return texts
