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
from .ollama_helper import get_ollama_client, correct_ocr_line


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

    # Build a JSON-serializable response (exclude non-serializable fields like 'process')
    response = {
        "status": job["status"],
        "source_name": job.get("source_name", ""),
    }

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
        response["progress"] = progress
    elif job["status"] == "failed":
        response["error"] = job.get("error", {"message": "Unknown error", "suggestion": None})

    return response


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


def extract_ollama_ocr(source_pdf: Path) -> List[Tuple[str, float]]:
    """
    Extract text using Ollama deepseek-ocr model.

    Returns:
        List of tuples: (text, confidence) for each page
    """
    settings = get_settings()
    client = get_ollama_client()

    if not settings.ollama_enabled or not client.is_available():
        LOGGER.warning("Ollama not available for OCR")
        return []

    try:
        # Convert PDF pages to images
        images = convert_from_path(str(source_pdf))
    except Exception as exc:
        LOGGER.error("Failed to convert PDF to images for Ollama OCR: %s", exc)
        return []

    results: List[Tuple[str, float]] = []

    for page_num, image in enumerate(images):
        try:
            # Use pytesseract to get raw text first, then correct with Ollama
            lang = settings.ocrmypdf_language or "eng"
            raw_text = pytesseract.image_to_string(image, lang=lang)

            # Correct each line with Ollama deepseek-ocr
            corrected_lines = []
            for line in raw_text.split("\n"):
                if line.strip():
                    corrected_line = correct_ocr_line(line.strip(), model=settings.ollama_ocr_model)
                    corrected_lines.append(corrected_line)
                else:
                    corrected_lines.append("")

            corrected_text = "\n".join(corrected_lines)

            # Estimate confidence based on corrections made
            # More corrections = lower confidence in original = higher confidence in corrected
            if raw_text != corrected_text:
                confidence = 85.0  # High confidence when corrections were made
            else:
                confidence = 75.0  # Medium confidence when no corrections needed

            results.append((corrected_text, confidence))

            LOGGER.info(
                "Ollama OCR for page %d: %d chars (confidence=%.2f)",
                page_num + 1,
                len(corrected_text),
                confidence
            )

        except Exception as exc:
            LOGGER.error("Failed Ollama OCR for page %d: %s", page_num + 1, exc)
            results.append(("", 0.0))

    return results


def compare_ocr_line(tesseract_line: str, ollama_line: str, tesseract_conf: float, ollama_conf: float) -> Tuple[str, str]:
    """
    Compare two OCR lines and select the best one based on confidence and heuristics.

    Returns:
        Tuple of (selected_text, source) where source is "tesseract", "ollama", or "hybrid"
    """
    # If either is empty, return the non-empty one
    if not tesseract_line.strip() and ollama_line.strip():
        return ollama_line, "ollama"
    if not ollama_line.strip() and tesseract_line.strip():
        return tesseract_line, "tesseract"
    if not tesseract_line.strip() and not ollama_line.strip():
        return "", "tesseract"

    # Check for genealogy-specific patterns
    import re

    # Generation markers
    gen_marker_patterns = [
        r"^\s*[IVX0-9DAPdap]{1,3}\s*--",  # Roman/Arabic/Letter + double dash
        r"^\s*[IVX0-9]{1,3}\.\s+",  # Roman/Arabic + period
    ]

    # Spouse marker
    spouse_pattern = r"^\s*sp-\s+"

    tesseract_has_gen = any(re.search(p, tesseract_line) for p in gen_marker_patterns)
    ollama_has_gen = any(re.search(p, ollama_line) for p in gen_marker_patterns)

    tesseract_has_spouse = bool(re.search(spouse_pattern, tesseract_line, re.IGNORECASE))
    ollama_has_spouse = bool(re.search(spouse_pattern, ollama_line, re.IGNORECASE))

    # Prefer Ollama if it has generation/spouse markers and Tesseract doesn't
    if ollama_has_gen and not tesseract_has_gen:
        return ollama_line, "ollama"
    if ollama_has_spouse and not tesseract_has_spouse:
        return ollama_line, "ollama"

    # Prefer Tesseract if it has generation/spouse markers and Ollama doesn't
    if tesseract_has_gen and not ollama_has_gen:
        return tesseract_line, "tesseract"
    if tesseract_has_spouse and not ollama_has_spouse:
        return tesseract_line, "tesseract"

    # If both have markers or neither has markers, use confidence scores
    if ollama_conf > tesseract_conf + 10:  # 10 point threshold
        return ollama_line, "ollama"
    elif tesseract_conf > ollama_conf + 10:
        return tesseract_line, "tesseract"
    else:
        # Similar confidence, prefer Ollama for its corrections
        return ollama_line, "ollama"


def merge_ocr_results(
    tesseract_text: str,
    ollama_text: str,
    tesseract_conf: float,
    ollama_conf: float
) -> Tuple[str, str, List[Dict]]:
    """
    Merge two OCR results by comparing line by line.

    Returns:
        Tuple of (final_text, overall_source, line_comparisons)
        - final_text: The selected text
        - overall_source: "tesseract", "ollama", or "hybrid"
        - line_comparisons: List of dicts with comparison details
    """
    tesseract_lines = tesseract_text.split("\n")
    ollama_lines = ollama_text.split("\n")

    # Pad shorter list with empty strings
    max_lines = max(len(tesseract_lines), len(ollama_lines))
    tesseract_lines.extend([""] * (max_lines - len(tesseract_lines)))
    ollama_lines.extend([""] * (max_lines - len(ollama_lines)))

    final_lines = []
    line_comparisons = []
    sources_used = {"tesseract": 0, "ollama": 0, "hybrid": 0}

    for i, (t_line, o_line) in enumerate(zip(tesseract_lines, ollama_lines)):
        selected_line, source = compare_ocr_line(t_line, o_line, tesseract_conf, ollama_conf)
        final_lines.append(selected_line)
        sources_used[source] += 1

        line_comparisons.append({
            "line_num": i + 1,
            "tesseract": t_line,
            "ollama": o_line,
            "selected": selected_line,
            "source": source,
        })

    final_text = "\n".join(final_lines)

    # Determine overall source
    if sources_used["ollama"] > sources_used["tesseract"] * 1.5:
        overall_source = "ollama"
    elif sources_used["tesseract"] > sources_used["ollama"] * 1.5:
        overall_source = "tesseract"
    else:
        overall_source = "hybrid"

    LOGGER.info(
        "Merged OCR: %d lines, source=%s (tesseract=%d, ollama=%d)",
        max_lines,
        overall_source,
        sources_used["tesseract"],
        sources_used["ollama"]
    )

    return final_text, overall_source, line_comparisons


def run_hybrid_ocr(source_pdf: Path) -> Dict:
    """
    Run hybrid OCR: both Tesseract (via pypdf) and Ollama deepseek-ocr.

    Returns:
        Dictionary with results for each page:
        {
            "pages": [
                {
                    "page_index": 0,
                    "tesseract_text": "...",
                    "ollama_text": "...",
                    "final_text": "...",
                    "tesseract_confidence": 85.0,
                    "ollama_confidence": 90.0,
                    "selected_source": "hybrid",
                    "line_comparisons": [...]
                },
                ...
            ]
        }
    """
    settings = get_settings()

    if not settings.ollama_enabled or not settings.ollama_use_hybrid_ocr:
        LOGGER.info("Hybrid OCR disabled, skipping")
        return {"pages": []}

    LOGGER.info("Starting hybrid OCR for %s", source_pdf.name)

    # Extract text with Tesseract (from OCRmyPDF output PDF)
    try:
        reader = PdfReader(str(source_pdf))
        tesseract_pages = [(page.extract_text() or "", 0.0) for page in reader.pages]
    except Exception as exc:
        LOGGER.error("Failed to extract Tesseract text: %s", exc)
        return {"pages": []}

    # Extract confidence scores
    try:
        confidence_data = extract_confidence_scores(source_pdf)
        # Update confidence scores
        tesseract_pages = [
            (text, conf[0] if i < len(confidence_data) else 0.0)
            for i, (text, _) in enumerate(tesseract_pages)
        ]
    except Exception as exc:
        LOGGER.warning("Failed to extract confidence scores: %s", exc)

    # Extract text with Ollama
    ollama_pages = extract_ollama_ocr(source_pdf)

    # Ensure both lists have the same length
    max_pages = max(len(tesseract_pages), len(ollama_pages))
    tesseract_pages.extend([("", 0.0)] * (max_pages - len(tesseract_pages)))
    ollama_pages.extend([("", 0.0)] * (max_pages - len(ollama_pages)))

    # Merge results page by page
    pages_data = []
    for page_index, ((t_text, t_conf), (o_text, o_conf)) in enumerate(zip(tesseract_pages, ollama_pages)):
        final_text, source, comparisons = merge_ocr_results(t_text, o_text, t_conf, o_conf)

        pages_data.append({
            "page_index": page_index,
            "tesseract_text": t_text,
            "ollama_text": o_text,
            "final_text": final_text,
            "tesseract_confidence": t_conf,
            "ollama_confidence": o_conf,
            "selected_source": source,
            "line_comparisons": comparisons,
        })

    LOGGER.info("Hybrid OCR completed for %s: %d pages", source_pdf.name, len(pages_data))

    return {"pages": pages_data}
