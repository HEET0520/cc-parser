import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
SAMPLE_DIR = BASE_DIR / "sample_statements"
SAMPLE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# LLM API keys (optional)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Pre-loaded sample statements
SAMPLE_STATEMENTS = {
    "Sample 1 - Axis Bank": "sample_statements/statement_1.pdf",
    "Sample 2 - IDFC Bank": "sample_statements/statement_2.pdf",
    "Sample 3 - HDFC Bank": "sample_statements/statement_3.pdf",
    "Sample 4 - ICICI Bank": "sample_statements/statement_4.pdf",
    "Sample 5 - SBI Card": "sample_statements/statement_5.pdf",
}
