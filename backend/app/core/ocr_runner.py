from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Callable
import uuid
import queue
import threading
import time

from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from pypdf import PdfReader

from .settings import Settings, get_settings


LOGGER = logging.getLogger(__name__)

# In-memory job store and queue. In a production environment, you would use a
# more robust solution like Redis or a database.
OCR_JOBS: Dict[str, Dict] = {}
OCR_JOB_QUEUE: queue.Queue = queue.Queue()
NOTIFICATIONS: List[Dict] = []

class OCRProcessError(RuntimeError):
    """Raised when the OCR subprocess exits unsuccessfully."""

    def __init__(self, message: str, suggestion: Optional[str] = None):
        super().__init__(message)
        self.suggestion = suggestion


def ocr_worker():
    """Worker thread to process OCR jobs from the queue."""
    while True:
        job_id, source_pdf, output_pdf = OCR_JOB_QUEUE.get()
        LOGGER.info(f"Starting OCR job {job_id} for {source_pdf.name}")
        
        settings = get_settings()
        cmd = build_ocr_cmd(source_pdf, output_pdf, settings)
        stderr_path = output_pdf.parent / f"{job_id}.stderr"

        with open(stderr_path, "w") as stderr_file:
            process = subprocess.Popen(cmd, stderr=stderr_file)

        OCR_JOBS[job_id] = {
            "process": process,
            "stderr_path": stderr_path,
            "output_pdf": output_pdf,
            "status": "running",
            "source_name": source_pdf.name,
        }

        process.wait()

        if process.returncode == 0:
            OCR_JOBS[job_id]["status"] = "completed"
            message = f"OCR for {source_pdf.name} completed successfully."
            NOTIFICATIONS.append({"id": str(uuid.uuid4()), "message": message, "type": "success"})
        else:
            OCR_JOBS[job_id]["status"] = "failed"
            with open(stderr_path, "r") as f:
                stderr = f.read()
            error_msg, suggestion = _analyze_ocr_error(process.returncode, stderr)
            OCR_JOBS[job_id]["error"] = {"message": error_msg, "suggestion": suggestion}
            message = f"OCR for {source_pdf.name} failed: {error_msg}"
            NOTIFICATIONS.append({"id": str(uuid.uuid4()), "message": message, "type": "error"})

        LOGGER.info(f"Finished OCR job {job_id}")
        OCR_JOB_QUEUE.task_done()


# Start the OCR worker thread
threading.Thread(target=ocr_worker, daemon=True).start()


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

    if settings.ocrmypdf_remove_background:
        cmd.append("--remove-background")

    fast_web_view_mb = settings.ocrmypdf_fast_web_view_mb
    if isinstance(fast_web_view_mb, int) and fast_web_view_mb > 0:
        cmd.extend(["--fast-web-view", str(fast_web_view_mb)])

    if settings.ocrmypdf_language:
        cmd.extend(["-l", settings.ocrmypdf_language])

    cmd.extend([str(input_pdf), str(output_pdf)])
    return cmd


def queue_ocr_job(source_pdf: Path, output_pdf: Path) -> str:
    """Queue an OCR job and return a job ID."""
    job_id = str(uuid.uuid4())
    OCR_JOB_QUEUE.put((job_id, source_pdf, output_pdf))
    OCR_JOBS[job_id] = {"status": "queued"}
    return job_id


def get_ocr_job_status(job_id: str) -> Dict:
    """Get the status of an OCR job."""
    job = OCR_JOBS.get(job_id)
    if not job:
        raise ValueError("Job not found")

    if job["status"] == "running":
        progress = {}
        with open(job["stderr_path"], "r") as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                # Example tqdm output:   2%| | 1/50 [00:01<01:02,  1.23it/s]
                parts = last_line.split()
                if len(parts) > 2 and "%" in parts[0]:
                    try:
                        percent = int(parts[0].replace("%", ""))
                        page_progress = parts[2].split("/")
                        current_page = int(page_progress[0])
                        total_pages = int(page_progress[1].replace("[", ""))
                        progress = {
                            "percent": percent,
                            "current_page": current_page,
                            "total_pages": total_pages,
                        }
                    except (ValueError, IndexError):
                        pass # Ignore parsing errors
        job["progress"] = progress

    return job


def get_ocr_result(job_id: str) -> list[str]:
    """Get the result of a completed OCR job."""
    job = OCR_JOBS.get(job_id)
    if not job:
        raise ValueError("Job not found")

    if job["status"] != "completed":
        raise ValueError("Job is not completed")

    reader = PdfReader(str(job["output_pdf"]))
    texts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        texts.append(text)
    return texts


def get_notifications() -> List[Dict]:
    """Get all notifications."""
    return NOTIFICATIONS


def clear_notification(notification_id: str):
    """Clear a specific notification."""
    global NOTIFICATIONS
    NOTIFICATIONS = [n for n in NOTIFICATIONS if n["id"] != notification_id]


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
            lang = settings.ocrmypdf_language or "eng"
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
