import fitz
import re
from typing import Optional, Dict, Any

class CCStatementParser:
    """
    Core regex-based parser.
    No LLM dependency - fast and reliable.
    """
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.raw_text = self._read_pdf()
    
    def _read_pdf(self) -> str:
        """Read PDF and extract text"""
        try:
            doc = fitz.open(self.pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            raise ValueError(f"Failed to read PDF: {e}")
    
    def extract_all(self) -> Dict[str, Any]:
        """Extract all 5 data points using regex"""
        data = {
            'card_last_4': self._get_card_number(),
            'statement_period': self._get_period(),
            'due_date': self._get_due_date(),
            'amount_due': self._get_amount(),
            'credit_limit': self._get_limit()
        }
        
        # Calculate confidence
        filled = sum(1 for v in data.values() if v is not None)
        data['confidence'] = 'high' if filled >= 4 else 'medium' if filled >= 2 else 'low'
        data['fields_extracted'] = filled
        data['extraction_method'] = 'regex'
        
        return data
    
    def _get_card_number(self) -> Optional[str]:
        """Extract last 4 digits of card number"""
        patterns = [
            r'\d{6}\*+(\d{4})',
            r'X{4}\s+(\d{4})',
            r'[X*]{4}\s[X*]{4}\s[X*]{4}\s(\d{4})',
            r'\*{8,}(\d{4})',
            r'ending.*?(\d{4})',
            r'Card\s+(?:Number|No\.?).*?(\d{4})(?:\s|$|<)',
            r'\d{4}[\s\-][X*]{4}[\s\-][X*]{4}[\s\-](\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _get_period(self) -> Optional[str]:
        """Extract statement period"""
        patterns = [
            r'(?:Statement Period|Billing Cycle|Billing Period)[:\s]+(\d{2}[/-]\d{2}[/-]\d{4}\s*[-to]+\s*\d{2}[/-]\d{2}[/-]\d{4})',
            r'From\s+(\d{2}[/-]\d{2}[/-]\d{4})\s+To\s+(\d{2}[/-]\d{2}[/-]\d{4})',
            r'(\d{2}/\d{2}/\d{4}\s*-\s*\d{2}/\d{2}/\d{4})',
            r'(\d{2}-\d{2}-\d{4}\s+to\s+\d{2}-\d{2}-\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    return f"{match.group(1)} - {match.group(2)}"
                return match.group(1)
        return None
    
    def _get_due_date(self) -> Optional[str]:
        """Extract payment due date"""
        patterns = [
            r'Payment Due Date[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})',
            r'Due Date[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})',
            r'Pay By[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})',
            r'Payment Deadline[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})',
            r'Last Date.*?Payment[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})',
            r'Due\s+on[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _get_amount(self) -> Optional[float]:
        """Extract total amount due"""
        patterns = [
            r'Total Payment Due\s+\*?[₹$]?\s*([0-9,]+\.?\d*)\s*(?:Dr|CR)?',
            r'Total Amount Due\s+\*?[₹$]?\s*([0-9,]+\.?\d*)',
            r'Amount Payable\s+[₹$]?\s*([0-9,]+\.?\d*)',
            r'Outstanding\s+(?:Amount|Balance)\s+[₹$]?\s*([0-9,]+\.?\d*)',
            r'New Balance\s+[₹$]?\s*([0-9,]+\.?\d*)',
            r'Total\s+Due\s+[₹$]?\s*([0-9,]+\.?\d*)',
            r'Amount\s+Due[:\s]+\*?[₹$]?\s*([0-9,]+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '').strip()
                    return float(amount_str)
                except (ValueError, AttributeError):
                    continue
        return None
    
    def _get_limit(self) -> Optional[float]:
        """Extract credit limit"""
        patterns = [
            r'Credit Limit\s+[₹$]?\s*([0-9,]+\.?\d*)',
            r'Total Credit Limit\s+[₹$]?\s*([0-9,]+\.?\d*)',
            r'Card Limit\s+[₹$]?\s*([0-9,]+\.?\d*)',
            r'(?:Total\s+)?Limit\s+[₹$]?\s*([0-9,]+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                try:
                    limit_str = match.group(1).replace(',', '').strip()
                    return float(limit_str)
                except (ValueError, AttributeError):
                    continue
        return None


def parse_with_regex(pdf_path: str) -> Dict[str, Any]:
    """Main regex extraction function"""
    parser = CCStatementParser(pdf_path)
    return parser.extract_all()
