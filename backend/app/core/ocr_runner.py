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

    def __init__(self, message: str, suggestion: Optional[str] = None):
        super().__init__(message)
        self.suggestion = suggestion


def _analyze_ocr_error(returncode: int, stderr: str) -> Tuple[str, Optional[str]]:
    """
    Analyze OCR error and provide helpful suggestions.

    Returns:
        Tuple of (error_message, suggestion)
    """
    stderr_lower = stderr.lower()

    # Missing language pack
    if "tesseract" in stderr_lower and ("language" in stderr_lower or "traineddata" in stderr_lower):
        return (
            "OCR failed: Missing Tesseract language pack",
            "Install the required Tesseract language pack. For English: 'brew install tesseract-lang' (macOS) or 'apt-get install tesseract-ocr-eng' (Ubuntu). For other languages, check tesseract documentation."
        )

    # Corrupted or invalid PDF
    if "pdf" in stderr_lower and ("corrupt" in stderr_lower or "invalid" in stderr_lower or "damaged" in stderr_lower):
        return (
            "OCR failed: PDF file appears corrupted or invalid",
            "Try opening the PDF in a viewer to verify it's valid. If corrupted, try re-downloading the file or using a PDF repair tool."
        )

    # Encrypted PDF
    if "encrypt" in stderr_lower or "password" in stderr_lower or "permission" in stderr_lower:
        return (
            "OCR failed: PDF is encrypted or password-protected",
            "Remove encryption from the PDF first using a PDF tool like 'qpdf --decrypt input.pdf output.pdf' or Adobe Acrobat."
        )

    # Out of memory
    if "memory" in stderr_lower or "oom" in stderr_lower:
        return (
            "OCR failed: Insufficient memory",
            "The PDF may be too large or high-resolution. Try reducing the PDF resolution or processing fewer pages at once."
        )

    # File not found / permission denied
    if "no such file" in stderr_lower or "not found" in stderr_lower:
        return (
            "OCR failed: Input file not found",
            "Verify that the file path is correct and the file exists on disk."
        )

    if "permission denied" in stderr_lower:
        return (
            "OCR failed: Permission denied",
            "Check file permissions and ensure the application has read/write access to the file and output directory."
        )

    # Timeout
    if returncode == -9 or "killed" in stderr_lower:
        return (
            "OCR failed: Process was killed (possibly timeout or out of memory)",
            "The file may be too large. Try increasing the timeout in settings or processing a smaller file."
        )

    # Generic error with exit code
    return (
        f"OCR failed with exit code {returncode}",
        "Check the application logs for more details. Common issues: missing dependencies, corrupted PDF, or unsupported PDF format."
    )


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
        message = f"OCR command timed out after {settings.ocrmypdf_timeout_secs} seconds"
        suggestion = "The PDF may be too large or complex. Try: 1) Increase the timeout in settings, 2) Split the PDF into smaller files, or 3) Reduce the PDF resolution."
        raise OCRProcessError(f"{message}\n\nSuggestion: {suggestion}", suggestion) from exc

    if result.returncode != 0:  # pragma: no cover - subprocess failure
        stderr = (result.stderr or "").strip()
        tail = "\n".join(stderr.splitlines()[-5:]) if stderr else ""
        LOGGER.error(
            "OCR command failed (exit %s): %s",
            result.returncode,
            tail or "no stderr output",
        )

        # Analyze error and provide helpful suggestion
        error_msg, suggestion = _analyze_ocr_error(result.returncode, stderr)
        full_message = error_msg
        if suggestion:
            full_message = f"{error_msg}\n\nSuggestion: {suggestion}"

        raise OCRProcessError(full_message, suggestion)

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
        error_str = str(exc).lower()

        # Provide helpful suggestions based on error type
        if "poppler" in error_str or "pdftoppm" in error_str:
            suggestion = "Install poppler-utils: 'brew install poppler' (macOS) or 'apt-get install poppler-utils' (Ubuntu)"
        elif "memory" in error_str:
            suggestion = "PDF may be too large. Try reducing PDF resolution or splitting into smaller files."
        else:
            suggestion = "Ensure pdf2image and poppler-utils are installed correctly."

        message = f"Failed to convert PDF to images: {exc}\n\nSuggestion: {suggestion}"
        raise OCRProcessError(message, suggestion) from exc

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
