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

# Pre-loaded sample statements (updated filenames)
SAMPLE_STATEMENTS = {
    "Sample 1 - Axis Bank": "F:/cc-parser/cc-parser/cc-parser/sample_statements/540819461-Credit-Card-Statement-1.pdf",
    "Sample 2 - IDFC Bank": "F:/cc-parser/cc-parser/cc-parser/sample_statements/576360491-IDFC-FIRST-Bank-Credit-Card-Statement-24052022.pdf",
    "Sample 3 - ICICI Bank": "F:/cc-parser/cc-parser/cc-parser/sample_statements/608920919-CreditCardStatement.pdf",
    "Sample 4 - HDFC Bank": "F:/cc-parser/cc-parser/cc-parser/sample_statements/636483454-credit-card-statement.pdf",
}
