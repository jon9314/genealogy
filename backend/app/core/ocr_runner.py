from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from pypdf import PdfReader

from .settings import Settings, get_settings


LOGGER = logging.getLogger(__name__)


class OCRProcessError(RuntimeError):
    """Raised when the OCR subprocess exits unsuccessfully."""


def build_ocr_cmd(input_pdf: Path, output_pdf: Path, settings: Settings) -> list[str]:
    """Construct the ocrmypdf command with optional tuning flags."""

    cmd: List[str] = [
        settings.ocrmypdf_executable,
        "--skip-text",  # Preserve existing text, only OCR image-only pages
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


def extract_confidence_scores(source_pdf: Path) -> List[Tuple[float, str]]:
    """
    Extract text with line-level confidence scores using pytesseract.

    Returns:
        List of tuples: (average_confidence, line_confidences_json) for each page
    """
    settings = get_settings()

    try:
        # Convert PDF pages to images
        images = convert_from_path(str(source_pdf))
    except Exception as exc:
        LOGGER.error("Failed to convert PDF to images: %s", exc)
        raise OCRProcessError(f"Failed to convert PDF to images: {exc}") from exc

    results: List[Tuple[float, str]] = []

    for page_num, image in enumerate(images):
        try:
            # Run Tesseract with detailed data output
            lang = settings.language or "eng"
            data = pytesseract.image_to_data(
                image,
                lang=lang,
                output_type=pytesseract.Output.DICT
            )

            # Group text by lines and calculate confidence scores
            line_confidences: List[Dict[str, any]] = []
            current_line: List[str] = []
            current_confidences: List[float] = []
            last_line_num = -1

            for i, conf in enumerate(data['conf']):
                line_num = data['line_num'][i]
                text = data['text'][i]

                # Filter out low-confidence noise (-1 means no text detected)
                if conf == -1 or not text.strip():
                    continue

                # New line detected
                if line_num != last_line_num and current_line:
                    # Save previous line
                    line_text = ' '.join(current_line)
                    avg_conf = sum(current_confidences) / len(current_confidences) if current_confidences else 0.0
                    line_confidences.append({
                        "line": last_line_num,
                        "text": line_text,
                        "confidence": round(avg_conf, 2)
                    })
                    current_line = []
                    current_confidences = []

                current_line.append(text)
                current_confidences.append(float(conf))
                last_line_num = line_num

            # Save last line
            if current_line:
                line_text = ' '.join(current_line)
                avg_conf = sum(current_confidences) / len(current_confidences) if current_confidences else 0.0
                line_confidences.append({
                    "line": last_line_num,
                    "text": line_text,
                    "confidence": round(avg_conf, 2)
                })

            # Calculate page average
            all_confs = [lc["confidence"] for lc in line_confidences]
            page_avg = sum(all_confs) / len(all_confs) if all_confs else 0.0

            results.append((
                round(page_avg, 2),
                json.dumps(line_confidences)
            ))

            LOGGER.info(
                "Extracted confidence for page %d: avg=%.2f, %d lines",
                page_num + 1,
                page_avg,
                len(line_confidences)
            )

        except Exception as exc:
            LOGGER.error("Failed to extract confidence for page %d: %s", page_num + 1, exc)
            # Return empty confidence for this page
            results.append((0.0, json.dumps([])))

    return results
