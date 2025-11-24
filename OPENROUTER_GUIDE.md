# OpenRouter LLM Integration Guide

## 🎯 Your Configuration

Your app is now configured to use **FREE OpenRouter LLM extensively**!

### Current Settings

```
LLM Provider: OpenRouter (cloud-based)
OCR Model: Qwen 2.5 VL 32B (free vision model)
Parse Model: Llama 3.3 70B (free text model - one of the best!)
Context Parsing: ENABLED
Confidence Threshold: 0.5 (uses LLM when OCR < 50% confident)
```

## 🚀 Quick Start

### Start the App

Double-click: `start_app.bat`

Or manually:
```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Access Points

- **Frontend UI**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🤖 How OpenRouter LLM is Used

### 1. **OCR Correction** (when enabled)
- Fixes common OCR errors in generation markers
- Examples: "D t-~" → "D--", "sp *-" → "sp-"
- Uses vision model: `qwen/qwen2.5-vl-32b-instruct:free`

### 2. **Context-Aware Parsing** (ENABLED)
- When regex patterns fail to parse a line
- When OCR confidence is below threshold (50%)
- Handles ambiguous or malformed text
- Uses text model: `meta-llama/llama-3.3-70b-instruct:free`

### 3. **Multi-Person Line Splitting**
- Detects lines with multiple people
- Example: "John (1850) sp- Mary (1855)" → separate entries
- Automatically splits and parses each person

## 📊 Test Results (Andrew Newcomb Chart)

- **294 persons** parsed successfully
- **99 families** created
- **92.5%** of persons have birth year data
- **12 generations** tracked correctly

## ⚙️ Tuning LLM Usage

### Use LLM More Aggressively

Edit `.env` to lower the confidence threshold:

```bash
# Use LLM for any line with OCR confidence < 30%
GENEALOGY_OLLAMA_CONFIDENCE_THRESHOLD=0.3

# Use LLM for almost everything (may be slow with free tier)
GENEALOGY_OLLAMA_CONFIDENCE_THRESHOLD=0.1
```

### Use LLM Less (Current: Moderate)

```bash
# Only use LLM for very low confidence OCR
GENEALOGY_OLLAMA_CONFIDENCE_THRESHOLD=0.7  # Default

# Rarely use LLM
GENEALOGY_OLLAMA_CONFIDENCE_THRESHOLD=0.9
```

## 🆓 Free Model Options

Your current models are excellent! But here are alternatives:

### Vision Models (for OCR)
```bash
# Current (32B params, very capable)
GENEALOGY_OPENROUTER_OCR_MODEL=qwen/qwen2.5-vl-32b-instruct:free

# Alternative (smaller, faster)
GENEALOGY_OPENROUTER_OCR_MODEL=nvidia/nemotron-nano-12b-v2-vl:free
```

### Text Models (for parsing)
```bash
# Current (70B params, best quality)
GENEALOGY_OPENROUTER_PARSE_MODEL=meta-llama/llama-3.3-70b-instruct:free

# Alternatives (faster, slightly lower quality)
GENEALOGY_OPENROUTER_PARSE_MODEL=qwen/qwen-2.5-72b-instruct:free
GENEALOGY_OPENROUTER_PARSE_MODEL=nousresearch/hermes-3-llama-3.1-405b:free
GENEALOGY_OPENROUTER_PARSE_MODEL=deepseek/deepseek-r1:free
```

### List All Available Models

```bash
python list_openrouter_models.py
```

## 💰 Rate Limits

Free models are rate-limited by OpenRouter:
- If you hit a rate limit, wait 30-60 seconds
- The app will fallback to regex parsing automatically
- Consider using paid models for heavy use (very cheap!)

### Paid Alternative (Minimal Cost)

Edit `.env` to use GPT-4o-mini (~$0.15 per 1M tokens):

```bash
GENEALOGY_OPENROUTER_OCR_MODEL=openai/gpt-4o-mini
GENEALOGY_OPENROUTER_PARSE_MODEL=openai/gpt-4o-mini
```

Expected cost: ~$0.01-0.05 per document

## 🔍 Monitoring LLM Usage

View LLM statistics via API:

```bash
curl http://localhost:8000/api/parse/llm-stats
```

Or in the app logs during parsing.

## 🎨 Workflow

1. **Upload PDF** → Frontend upload page
2. **Run OCR** → Tesseract extracts text
3. **Parse** → Regex patterns + OpenRouter LLM fallback
4. **Review** → Table/Graph view to verify data
5. **Export** → GEDCOM or CSV

## 📝 Tips for Best Results

1. **Let LLM Help**: Keep confidence threshold at 0.5 or lower
2. **Use Context Parse**: Always enabled (it's the best feature!)
3. **Monitor Stats**: Check LLM success rate in parse logs
4. **Test Models**: Try different free models to find your favorite

## 🆘 Troubleshooting

### "Rate limited upstream"
- Wait 60 seconds and retry
- Or switch to a different free model
- Or add credits to OpenRouter account

### "No endpoints found for model"
- Model name is incorrect
- Run `python list_openrouter_models.py` to see valid names

### Backend not loading .env
- Make sure `.env` is in the root directory `C:\genealogy\.env`
- Restart backend after changing `.env`

## ✅ Verification

Test that OpenRouter is working:

```bash
python test_openrouter.py
```

Test full parsing pipeline:

```bash
python test_parsing_only.py
```

---

**You're all set!** 🎉

Your genealogy app now uses free, cloud-based LLM extensively with **zero local memory overhead**!
