import json
import os
from typing import Dict, Any

class LLMExtractor:
    """
    Separate LLM-based extraction.
    Only triggered when user explicitly requests it.
    """
    
    def __init__(self, provider: str = "groq"):
        self.provider = provider
        self._validate_api_key()
    
    def _validate_api_key(self):
        """Check if API key exists"""
        if self.provider == "groq":
            if not os.getenv("GROQ_API_KEY"):
                raise ValueError("GROQ_API_KEY not set. Get free key at: https://console.groq.com")
        elif self.provider == "gemini":
            if not os.getenv("GEMINI_API_KEY"):
                raise ValueError("GEMINI_API_KEY not set. Get key at: https://ai.google.dev")
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract using LLM.
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Dictionary with extracted data
        """
        # Read PDF
        import fitz
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        # Extract using chosen provider
        if self.provider == "groq":
            result = self._extract_with_groq(text)
        elif self.provider == "gemini":
            result = self._extract_with_gemini(text)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
        
        # Add metadata
        result['extraction_method'] = f'llm_{self.provider}'
        
        # Calculate confidence
        filled = sum(1 for k in ['card_last_4', 'statement_period', 'due_date', 'amount_due', 'credit_limit'] 
                    if result.get(k) is not None)
        result['confidence'] = 'high' if filled >= 4 else 'medium' if filled >= 2 else 'low'
        result['fields_extracted'] = filled
        
        return result
    
    def _extract_with_groq(self, text: str) -> Dict[str, Any]:
        """Extract using Groq (fast and free)"""
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Install groq: pip install groq")
        
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        tools = [{
            "type": "function",
            "function": {
                "name": "extract_cc_data",
                "description": "Extract credit card statement fields",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "card_last_4": {"type": "string"},
                        "statement_period": {"type": "string"},
                        "due_date": {"type": "string"},
                        "amount_due": {"type": "number"},
                        "credit_limit": {"type": "number"}
                    }
                }
            }
        }]
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Extract credit card data accurately."},
                {"role": "user", "content": f"Extract:\n{text[:5000]}"}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "extract_cc_data"}},
            temperature=0
        )
        
        return json.loads(response.choices[0].message.tool_calls[0].function.arguments)
    
    def _extract_with_gemini(self, text: str) -> Dict[str, Any]:
        """Extract using Gemini"""
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("Install google-generativeai: pip install google-generativeai")
        
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        schema = {
            "type": "object",
            "properties": {
                "card_last_4": {"type": "string"},
                "statement_period": {"type": "string"},
                "due_date": {"type": "string"},
                "amount_due": {"type": "number"},
                "credit_limit": {"type": "number"}
            }
        }
        
        config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema
        )
        
        prompt = f"""Extract these fields from credit card statement:
- card_last_4: Last 4 digits
- statement_period: Date range
- due_date: Payment due date
- amount_due: Total amount (number)
- credit_limit: Credit limit (number)

Text:
{text[:5000]}
"""
        
        response = model.generate_content(prompt, generation_config=config)
        return json.loads(response.text)


def extract_with_llm(pdf_path: str, provider: str = "groq") -> Dict[str, Any]:
    """
    Main LLM extraction function.
    
    Args:
        pdf_path: Path to PDF
        provider: 'groq' or 'gemini'
    
    Returns:
        Extracted data dictionary
    """
    extractor = LLMExtractor(provider)
    return extractor.extract(pdf_path)
