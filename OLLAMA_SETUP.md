# Ollama Integration Setup

This document explains how to set up and use the Ollama LLM integration for improved OCR quality and parsing accuracy.

## Overview

The genealogy parser now supports two LLM-assisted features:

1. **Hybrid OCR**: Uses both Tesseract (via OCRmyPDF) and Ollama deepseek-ocr for OCR, then selects the best result per line based on confidence and genealogy-specific heuristics.

2. **Context-Aware Parsing**: Uses Ollama qwen3:8b to parse ambiguous lines that fail regex parsing, handling edge cases like:
   - Multiple people on one line
   - Unclear generation markers
   - Complex date formats
   - Low OCR confidence

## Prerequisites

### 1. Install Ollama

**Windows:**
```bash
# Download from https://ollama.com/download
# Or use winget:
winget install Ollama.Ollama
```

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Pull Required Models

```bash
# OCR correction model (3B parameters)
ollama pull deepseek-ocr:3b

# Parsing model (8B parameters)
ollama pull qwen3:8b
```

### 3. Verify Ollama is Running

```bash
# Check Ollama service status
ollama list

# Should show both models:
# deepseek-ocr:3b
# qwen3:8b
```

## Configuration

### Environment Variables

Add these to your `.env` file or set as environment variables with the `GENEALOGY_` prefix:

```bash
# Enable Ollama integration
GENEALOGY_OLLAMA_ENABLED=true

# Ollama server URL (default: http://localhost:11434)
GENEALOGY_OLLAMA_BASE_URL=http://localhost:11434

# Model configuration
GENEALOGY_OLLAMA_OCR_MODEL=deepseek-ocr:3b
GENEALOGY_OLLAMA_PARSE_MODEL=qwen3:8b

# Timeout for LLM requests (seconds, default: 30)
GENEALOGY_OLLAMA_TIMEOUT_SECS=30

# Feature flags
GENEALOGY_OLLAMA_USE_HYBRID_OCR=true
GENEALOGY_OLLAMA_USE_CONTEXT_PARSE=true

# Confidence threshold for LLM fallback (0.0-1.0, default: 0.7)
# Lines with OCR confidence below this will be re-parsed with LLM
GENEALOGY_OLLAMA_CONFIDENCE_THRESHOLD=0.7
```

### Minimal Configuration

For quick testing, only these are required:

```bash
GENEALOGY_OLLAMA_ENABLED=true
```

All other settings use sensible defaults.

## Usage

### Hybrid OCR Workflow

1. **Upload PDF** as usual
2. **Run OCR** - If Ollama is enabled and running, hybrid OCR will automatically:
   - Run OCRmyPDF (Tesseract)
   - Run deepseek-ocr for comparison
   - Compare results line by line
   - Select best text based on:
     - Generation markers (II--, III--, sp-, etc.)
     - Confidence scores
     - Genealogy-specific patterns
3. **Review comparison** via API:
   ```bash
   GET /api/ocr/{source_id}/hybrid-comparison
   ```

### Context-Aware Parsing Workflow

1. **Parse OCR text** as usual
2. When regex parsing fails, the LLM automatically:
   - Attempts to parse the line using qwen3:8b
   - Extracts structured data (generation, name, dates)
   - Handles multi-person lines
   - Falls back to flagged lines if LLM also fails
3. **View LLM statistics** via API:
   ```bash
   GET /api/parse/llm-stats
   ```

### API Endpoints

#### OCR Endpoints

- `GET /api/ocr/{source_id}/hybrid-comparison`
  - Get line-by-line comparison between Tesseract and Ollama
  - Shows which source was selected for each line
  - Useful for debugging and quality assessment

- `GET /api/ocr/{source_id}/confidence`
  - Get detailed confidence score breakdown
  - Shows per-page and per-line confidence scores
  - Includes OCR source information (tesseract/ollama/hybrid)

#### Parsing Endpoints

- `GET /api/parse/llm-stats`
  - Get LLM parsing statistics
  - Shows success rate, total attempts, multi-person splits
  - Displays model configuration

- `POST /api/parse/llm-stats/reset`
  - Reset LLM parsing statistics
  - Useful for benchmarking after configuration changes

## Performance Considerations

### Speed

- **Hybrid OCR**: Adds ~2-5 seconds per page (depends on page complexity)
- **LLM Parsing**: Only runs for ambiguous lines (typically <5% of lines)
- **Recommendation**: Enable for final production runs, disable for quick tests

### Resource Usage

- **RAM**: qwen3:8b requires ~8GB RAM
- **VRAM**: GPU acceleration supported but not required
- **CPU**: Works well on modern CPUs (4+ cores recommended)

### Optimization Tips

1. **Disable features you don't need:**
   ```bash
   GENEALOGY_OLLAMA_USE_HYBRID_OCR=false  # Disable if OCR is already good
   GENEALOGY_OLLAMA_USE_CONTEXT_PARSE=true  # Keep for better parsing
   ```

2. **Adjust confidence threshold:**
   ```bash
   # Higher = less LLM usage (faster)
   GENEALOGY_OLLAMA_CONFIDENCE_THRESHOLD=0.8

   # Lower = more LLM usage (more accurate)
   GENEALOGY_OLLAMA_CONFIDENCE_THRESHOLD=0.6
   ```

3. **Use smaller models (if available):**
   ```bash
   GENEALOGY_OLLAMA_PARSE_MODEL=qwen3:4b  # Smaller, faster
   ```

## Troubleshooting

### Ollama Not Available

**Symptom**: API returns "Ollama not available"

**Solutions**:
1. Check Ollama is running:
   ```bash
   ollama list
   ```
2. Verify URL:
   ```bash
   curl http://localhost:11434/api/version
   ```
3. Check firewall settings
4. Restart Ollama service

### Models Not Found

**Symptom**: "model not found" errors

**Solution**: Pull models explicitly:
```bash
ollama pull deepseek-ocr:3b
ollama pull qwen3:8b
```

### Slow Performance

**Symptom**: OCR/parsing takes too long

**Solutions**:
1. Disable hybrid OCR if Tesseract is already accurate:
   ```bash
   GENEALOGY_OLLAMA_USE_HYBRID_OCR=false
   ```
2. Increase confidence threshold to reduce LLM usage:
   ```bash
   GENEALOGY_OLLAMA_CONFIDENCE_THRESHOLD=0.8
   ```
3. Use GPU acceleration (if available):
   - Ollama automatically uses GPU if detected
   - Check with: `ollama ps`

### High Memory Usage

**Symptom**: System running out of RAM

**Solutions**:
1. Close other applications
2. Use smaller models (if available)
3. Process files one at a time
4. Disable hybrid OCR (saves ~4GB RAM)

## Accuracy Improvements

### Expected Improvements

Based on testing with problematic genealogy PDFs:

- **OCR Quality**: 20-50% reduction in generation marker errors (D--, A--, etc.)
- **Parse Coverage**: 40-80% reduction in flagged lines
- **Relationship Accuracy**: 10-30% improvement in parent-child linking

### Measuring Accuracy

Use the included accuracy measurement scripts:

```bash
# Run accuracy check
python check_accuracy_v2.py

# View LLM statistics
curl http://localhost:8000/api/parse/llm-stats
```

### When to Use LLM Integration

**Use hybrid OCR when:**
- Scanned documents have poor quality
- Generation markers are frequently misread
- OCR confidence scores are consistently low (<70%)

**Use context-aware parsing when:**
- Many lines fail regex parsing
- Complex multi-person lines are common
- Need to handle edge cases automatically

**Skip LLM integration when:**
- OCR quality is already excellent
- Speed is critical
- Processing thousands of pages in batch

## Architecture

### Hybrid OCR Flow

```
PDF Input
  ↓
OCRmyPDF (Tesseract)
  ↓
deepseek-ocr (via Ollama)
  ↓
Line-by-line comparison
  ↓
Best text selection (confidence + heuristics)
  ↓
Store both results + selected text
```

### Context-Aware Parsing Flow

```
OCR Text Line
  ↓
Regex Pattern Matching
  ↓
Match? → No → LLM Parsing (qwen3:8b)
  ↓              ↓
Yes            Success? → Yes → Extract structured data
  ↓              ↓
Parse         No
  ↓              ↓
Store         Flag line
```

## Examples

### Example 1: Correcting Generation Markers

**Before (Tesseract):**
```
D t-~ John Smith (1850-1920)
```

**After (deepseek-ocr):**
```
D-- John Smith (1850-1920)
```

### Example 2: Multi-Person Line Splitting

**Input:**
```
II-- Jane Doe (1880-1960) sp- Bob Doe (1875-)
```

**LLM Output:**
```json
[
  {
    "generation": 2,
    "name": "Jane Doe",
    "birth_year": 1880,
    "death_year": 1960,
    "is_spouse": false
  },
  {
    "generation": 2,
    "name": "Bob Doe",
    "birth_year": 1875,
    "is_spouse": true
  }
]
```

### Example 3: Ambiguous Generation Inference

**Input:**
```
Sarah Brown (abt 1845-1920)
```

**Context:**
```json
{
  "last_gen": 2,
  "previous_person": "John Brown"
}
```

**LLM Output:**
```json
{
  "generation": 3,
  "name": "Sarah Brown",
  "birth_year": 1845,
  "death_year": 1920,
  "birth_approx": true,
  "is_spouse": false,
  "confidence": 0.85
}
```

## Future Enhancements

Potential improvements for future versions:

1. **Batch Processing**: Process multiple lines in one LLM call
2. **Custom Prompts**: Allow user-defined prompt templates
3. **Model Selection**: Support for additional Ollama models
4. **Confidence Tuning**: Per-source confidence threshold adjustment
5. **Feedback Loop**: Learn from user corrections to improve prompts

## Support

For issues or questions:
- GitHub Issues: https://github.com/jon9314/genealogy/issues
- Check logs: `backend_logs.txt`
- View LLM stats: `GET /api/parse/llm-stats`
