# Credit Card Statement Parser

Production-ready parser with **dual extraction modes**: Fast Regex or Intelligent AI.

## Features

✅ **5 Pre-loaded Samples** - Test immediately  
✅ **Custom Upload** - Use your own PDFs  
✅ **Dual Mode** - Choose Regex (fast) or AI (smart)  
✅ **No API Required** - Regex works out of the box  
✅ **Universal** - Works with any bank statement  

## Quick Start

### Setup

Install
pip install pymupdf streamlit

Run
streamlit run app.py

### Add Sample Statements

Place your test PDFs in `sample_statements/`:
sample_statements/
├── statement_1.pdf
├── statement_2.pdf
├── statement_3.pdf
├── statement_4.pdf
└── statement_5.pdf

The app will automatically detect and show them in the dropdown.

### Using AI Extraction (Optional)

Install AI libraries
pip install groq google-generativeai python-dotenv

Create .env file
echo "GROQ_API_KEY=your_key_here" > .env

Or enter API key directly in the UI sidebar

Get free API keys:
- Groq: https://console.groq.com (FREE, 500+ tokens/sec)
- Gemini: https://ai.google.dev ($0.075/1M tokens)

## Usage

### Web UI

1. **Run**: `streamlit run app.py`
2. **Select extraction mode**: Regex or AI
3. **Choose PDF**: Pick from dropdown or upload custom
4. **Extract**: Click the extract button
5. **Download**: Get JSON output

### Extraction Modes

**Regex Mode (Default)**
- No API key needed
- Instant results (< 1 second)
- Works on standard formats
- Free forever

**AI Mode (On-Demand)**
- Requires API key
- 1-2 seconds with Groq
- Handles unusual formats
- Optional feature

## Extracted Fields

1. Card Last 4 Digits
2. Statement Period
3. Payment Due Date
4. Total Amount Due
5. Credit Limit

## Architecture
parser.py → Regex extraction (core)
llm_extractor.py → AI extraction (separate, optional)
app.py → UI with dropdown + upload
config.py → Configuration


## Why Two Modes?

- **Regex**: Fast, reliable, works offline - perfect for standard PDFs
- **AI**: Handles edge cases, unusual formats - use when regex fails

Most statements work fine with Regex. AI is there when you need it.

## Demo Tips

1. Show regex extraction first (instant, free)
2. Demo a difficult PDF with AI extraction
3. Compare results side-by-side
4. Highlight the flexibility of choosing modes

#!/bin/bash

# Setup script for quick deployment

echo "Setting up CC Statement Parser..."

# Create directories
mkdir -p sample_statements
mkdir -p outputs

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install core dependencies
pip install pymupdf streamlit

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Place your sample PDFs in sample_statements/"
echo "2. Run: streamlit run app.py"
echo ""
echo "Optional: For AI extraction, install:"
echo "  pip install groq google-generativeai python-dotenv"
echo ""

