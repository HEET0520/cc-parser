import os
import re
import fitz
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

FIELD_LABELS = {
    'card_last_4': [
        r'card\s+(?:no|number)',
        r'card\s+ending',
        r'aan',
    ],
    'statement_period': [
        r'statement\s+period',
        r'billing\s+period',
        r'statement\s+date',
    ],
    'due_date': [
        r'payment\s+due\s+date',
        r'due\s+date',
        r'pay\s+by',
    ],
    'amount_due': [
        r'total\s+payment\s+due',
        r'total\s+amount\s+due',
        r'total\s+dues',
        r'amount\s+due',
        r'minimum\s+amount\s+due',
    ],
    'credit_limit': [
        r'total\s+credit\s+limit',
        r'credit\s+limit',
    ],
}

SUMMARY_HEADERS = [r'payment\s+summary', r'statement\s+summary', r'account\s+summary', r'credit\s+summary']
TRANSACTION_ANCHORS = [r'transactions?', r'domestic\s+transactions', r'your\s+transactions']
NOISE_PATTERNS = re.compile(r'(reward|points|3x|6x|bonus|cashback|igst|gst|convenience|promo)', re.I)

class CCStatementParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.base_name = Path(pdf_path).stem
        self.debug_log = []
        
        self.tables = self._extract_tables()
        self.blocks = self._extract_blocks()
        self.raw_text = self._extract_text()
        
        self._save_artifacts()
    
    def _extract_tables(self) -> List[List[List[str]]]:
        if not PDFPLUMBER_AVAILABLE:
            self.debug_log.append("pdfplumber not available")
            return []
        
        tables = []
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            cleaned = [[str(cell or '').strip() for cell in row] for row in table]
                            tables.append(cleaned)
                        self.debug_log.append(f"Page {page_num+1}: {len(page_tables)} table(s)")
        except Exception as e:
            self.debug_log.append(f"Table error: {e}")
        
        return tables
    
    def _extract_blocks(self) -> List[Dict]:
        blocks = []
        try:
            doc = fitz.open(self.pdf_path)
            for page_num, page in enumerate(doc):
                page_blocks = page.get_text("dict")["blocks"]
                for block in page_blocks:
                    if "lines" in block:
                        text = " ".join(
                            span["text"] 
                            for line in block["lines"] 
                            for span in line["spans"]
                        )
                        blocks.append({
                            'text': text,
                            'bbox': block['bbox'],
                            'page': page_num
                        })
            doc.close()
            self.debug_log.append(f"Extracted {len(blocks)} blocks")
        except Exception as e:
            self.debug_log.append(f"Block error: {e}")
        
        return blocks
    
    def _extract_text(self) -> str:
        try:
            doc = fitz.open(self.pdf_path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return self._normalize_currency(text)
        except Exception as e:
            self.debug_log.append(f"Text error: {e}")
            return ""
    
    def _normalize_currency(self, text: str) -> str:
        # Replace rupee symbols and variants
        text = text.replace('₹', ' CURR ')
        text = text.replace('`', ' CURR ')
        text = text.replace('Rs.', ' CURR ')
        text = re.sub(r'\(in\s+Rs\.\)', '', text)
        # Handle 'r' before numbers, with or without space (case insensitive)
        text = re.sub(r'(?i)([ \n\t\r\f\v]*)?r(?=[0-9,]+\.?\d*)', r'\1CURR ', text)
        # Normalize Dr/Cr to separate words for easier ignoring
        text = re.sub(r'\s+Dr\b', ' Dr', text)
        text = re.sub(r'\s+Cr\b', ' Cr', text)
        # Clean extra spaces but preserve some structure for dates
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _save_artifacts(self):
        os.makedirs("outputs", exist_ok=True)
        
        with open(f"outputs/{self.base_name}_raw_text.txt", "w", encoding="utf-8") as f:
            f.write(self.raw_text)
        
        with open(f"outputs/{self.base_name}_tables.json", "w", encoding="utf-8") as f:
            json.dump(self.tables, f, indent=2, ensure_ascii=False)
        
        with open(f"outputs/{self.base_name}_blocks.json", "w", encoding="utf-8") as f:
            json.dump(self.blocks, f, indent=2, ensure_ascii=False)
    
    def _find_summary_zone(self, sorted_blocks: List[Dict]) -> Tuple[int, int]:
        start = 0
        end = len(sorted_blocks) - 1
        for idx, block in enumerate(sorted_blocks):
            if any(re.search(pat, block['text'].lower()) for pat in SUMMARY_HEADERS):
                start = max(0, idx - 5)
            if any(re.search(pat, block['text'].lower()) for pat in TRANSACTION_ANCHORS):
                end = idx
                break
        return start, end
    
    def _extract_by_type(self, field_name: str, text: str) -> Optional[Any]:
        text = text.strip()
        if not text:
            return None
        
        if field_name == 'card_last_4':
            groups = re.findall(r'(\d{4})', text)
            if groups:
                for g in reversed(groups):
                    if len(g) == 4 and g.isdigit():
                        return g
        
        elif field_name == 'statement_period':
            # Range patterns
            match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})\s*[-to]+\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.I)
            if match:
                return f"{match.group(1)} to {match.group(2)}"
            match = re.search(r'(\w+\s+\d{1,2},\s+\d{4})\s+to\s+(\w+\s+\d{1,2},\s+\d{4})', text, re.I)
            if match:
                return f"{match.group(1)} to {match.group(2)}"
            # Single date fallback
            match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
            if match:
                return match.group(1)
            match = re.search(r'(\w+\s+\d{1,2},\s+\d{4})', text)
            if match:
                return match.group(1)
        
        elif field_name == 'due_date':
            match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})|(\w+\s+\d{1,2},\s+\d{4})|(immediate)', text, re.I)
            if match:
                return match.group(1) or match.group(2) or 'Immediate'
        
        elif field_name in ['amount_due', 'credit_limit']:
            candidates = re.findall(r'([0-9,]+\.?\d*)', text)
            for cand in candidates:
                amt_str = cand.replace(',', '')
                try:
                    amt = float(amt_str)
                    min_val = 1000 if field_name == 'credit_limit' else 50
                    max_val = 50000000 if field_name == 'credit_limit' else 1000000
                    if min_val < amt < max_val:
                        return amt
                except ValueError:
                    pass
            return None
        
        return None
    
    def _find_in_tables(self, field_name: str, patterns: List[str]) -> Tuple[Optional[Any], Optional[str]]:
        for table_idx, table in enumerate(self.tables):
            for row_idx, row in enumerate(table):
                for cell_idx, cell in enumerate(row):
                    cell_lower = cell.lower()
                    for pattern in patterns:
                        if re.search(pattern, cell_lower):
                            candidates = []
                            for i in range(cell_idx + 1, len(row)):
                                candidates.append(row[i])
                            for r in range(row_idx + 1, len(table)):
                                if cell_idx < len(table[r]):
                                    candidates.append(table[r][cell_idx])
                            for cand in candidates[:3]:
                                val = self._extract_by_type(field_name, cand)
                                if val is not None:
                                    self.debug_log.append(f"{field_name}: table match → '{val}'")
                                    return val, f"table:{pattern}"
        return None, None
    
    def _find_in_blocks(self, field_name: str, patterns: List[str]) -> Tuple[Optional[Any], Optional[str]]:
        sorted_blocks = sorted(self.blocks, key=lambda b: (b['page'], b['bbox'][1], b['bbox'][0]))
        summary_start, summary_end = self._find_summary_zone(sorted_blocks)
        
        for idx in range(summary_start, min(summary_end + 10, len(sorted_blocks))):
            block = sorted_blocks[idx]
            block_lower = block['text'].lower()
            if NOISE_PATTERNS.search(block['text']):
                continue
            for pattern in patterns:
                if re.search(pattern, block_lower):
                    val = self._extract_by_type(field_name, block['text'])
                    if val is not None:
                        self.debug_log.append(f"{field_name}: block match → '{val}'")
                        return val, f"block:{pattern}"
                    for offset in range(1, min(6, len(sorted_blocks) - idx)):
                        next_block = sorted_blocks[idx + offset]
                        if abs(next_block['bbox'][0] - block['bbox'][0]) < 100:
                            val = self._extract_by_type(field_name, next_block['text'])
                            if val is not None:
                                self.debug_log.append(f"{field_name}: nearby block match → '{val}'")
                                return val, f"block-near:{pattern}"
        return None, None
    
    def _global_search(self, field_name: str) -> Tuple[Optional[Any], Optional[str]]:
        self.debug_log.append(f"{field_name}: trying global search")
        
        if field_name == 'card_last_4':
            patterns = [
                r'card\s+(?:no|number)[:\s]*.*?(\d{4})\s*[\*X]{4,}$',
                r'(\d{4})\s*X{4,}\s*(\d{4})',
                r'(\d{4})\s+X{4,}\s+X{4,}\s+(\d{4})',
                r'XXXX\s+(\d{4})',
                r'X{4}\s+(\d{4})',
                r'card\s+no[:\s]*.*?(\d{4})$',
            ]
            for pat in patterns:
                match = re.search(pat, self.raw_text, re.I)
                if match:
                    groups = [g for g in match.groups() if g and g.isdigit() and len(g) == 4]
                    if groups:
                        val = groups[-1]
                        self.debug_log.append(f"card_last_4: global found '{val}' with pattern {pat}")
                        return val, "global"
        
        elif field_name == 'statement_period':
            # Enhanced with date sorting near label, longer snippet
            date_pattern = r'\d{1,2}/\d{1,2}/\d{4}'
            label_match = re.search(r'statement\s+period', self.raw_text, re.I)
            if label_match:
                start = label_match.end()
                snippet = self.raw_text[start:start + 1000]  # Longer snippet for RBL
                snippet_dates = re.findall(date_pattern, snippet)
                self.debug_log.append(f"Snippet dates: {snippet_dates}")
                valid_snippet = []
                for sd in snippet_dates:
                    try:
                        sd_date = datetime.strptime(sd, '%d/%m/%Y')
                        valid_snippet.append((sd_date, sd))
                    except ValueError:
                        pass
                self.debug_log.append(f"Valid dates: {valid_snippet}")
                if len(valid_snippet) >= 2:
                    valid_snippet.sort(key=lambda x: x[0])
                    period = f"{valid_snippet[0][1]} to {valid_snippet[1][1]}"
                    self.debug_log.append(f"statement_period: sorted snippet dates → '{period}'")
                    return period, "global"
            
            # Original range patterns as fallback
            range_patterns = [
                r'statement\s+(?:period|date)\s*[:\s]*(\d{1,2}/\d{1,2}/\d{4})\s*[-to]+\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})\s*[-to]+\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'(\w+\s+\d{1,2},\s+\d{4})\s+to\s+(\w+\s+\d{1,2},\s+\d{4})',
            ]
            for pat in range_patterns:
                match = re.search(pat, self.raw_text, re.I)
                if match:
                    return f"{match.group(1)} to {match.group(2)}", "global"
            
            # Single date
            single_patterns = [
                r'statement\s+(?:date|period)\s*[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
                r'billing\s+(?:date|period)\s*[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
                r'statement\s+(?:date|period)\s*[:\s]*(\w+\s+\d{1,2},\s+\d{4})',
            ]
            for pat in single_patterns:
                match = re.search(pat, self.raw_text, re.I)
                if match:
                    return match.group(1), "global"
        
        elif field_name == 'due_date':
            # Prioritize Immediate patterns first
            imm_patterns = [
                r'payment\s+due\s+date\s*[:=]?\s*(immediate)',
                r'(?:payment\s+due\s+date|due\s+date).*?(immediate)',
            ]
            for pat in imm_patterns:
                match = re.search(pat, self.raw_text, re.I)
                if match:
                    val = 'Immediate'
                    self.debug_log.append(f"due_date: global found '{val}' with pattern {pat}")
                    return val, "global"
            
            # Then date patterns
            patterns = [
                r'payment\s+due\s+date\s*[:=]?\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'due\s+date\s*[:=]?\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'payment\s+due\s+date\s*[:=]?\s*(\w+\s+\d{1,2},\s+\d{4})',
                r'due\s+date\s*[:=]?\s*(\w+\s+\d{1,2},\s+\d{4})',
            ]
            for pat in patterns:
                match = re.search(pat, self.raw_text, re.I)
                if match:
                    val = match.group(1)
                    self.debug_log.append(f"due_date: global found '{val}' with pattern {pat}")
                    return val, "global"
        
        elif field_name in ['amount_due', 'credit_limit']:
            if field_name == 'amount_due':
                label = r'total\s+(?:payment\s+)?(?:amount\s+)?due|total\s+dues'
            else:
                label = r'(?:total\s+)?credit\s+limit'
            patterns = [
                rf'{label}\s*[:=]?\s*(?:CURR\s*)?\s*([0-9,]+\.?\d*)\s*(?:Dr)?',
                rf'{label}\b\s*[:=]?\s*(?:CURR\s*)?\s*([0-9,]+\.?\d*)\s*(?:Dr)?',
                rf'{label}\b.*?\s*([0-9,]+\.?\d*)\s*(?:Dr)?',
            ]
            for pat in patterns:
                match = re.search(pat, self.raw_text, re.I)
                if match and match.group(1):
                    amt_str = match.group(1).replace(',', '')
                    try:
                        amt = float(amt_str)
                        min_val = 50 if field_name == 'amount_due' else 1000
                        max_val = 1000000 if field_name == 'amount_due' else 5000000
                        if min_val < amt < max_val:
                            self.debug_log.append(f"{field_name}: global found {amt} with {pat}")
                            return amt, "global"
                    except ValueError:
                        pass
            # Fallback: largest reasonable number near summary keywords
            summary_keywords = r'(account\s+summary|total\s+amount\s+due|credit\s+limit)'
            summary_match = re.search(summary_keywords + r'.*?([0-9,]+\.?\d*)', self.raw_text, re.I | re.DOTALL)
            if summary_match and summary_match.group(1):
                amt_str = summary_match.group(1).replace(',', '')
                try:
                    amt = float(amt_str)
                    if (field_name == 'amount_due' and 100 < amt < 500000) or (field_name == 'credit_limit' and 5000 < amt < 1000000):
                        return amt, "global-fallback"
                except:
                    pass
        
        return None, None
    
    def extract(self) -> Dict[str, Any]:
        result = {}
        alerts = []
        
        for field_name, patterns in FIELD_LABELS.items():
            value = None
            source = None
            
            try:
                if self.tables:
                    value, source = self._find_in_tables(field_name, patterns)
                
                if value is None and self.blocks:
                    value, source = self._find_in_blocks(field_name, patterns)
                
                if value is None:
                    value, source = self._global_search(field_name)
                
                # Post-process for amounts if needed
                if field_name in ['amount_due', 'credit_limit'] and isinstance(value, str):
                    amt_str = value.replace(',', '')
                    try:
                        value = float(amt_str)
                    except:
                        value = None
                        
                # For due_date, if None, it will trigger alert
            except Exception as e:
                self.debug_log.append(f"{field_name}: extraction failed with error: {e}")
            
            result[field_name] = value
            result[f'{field_name}_pattern'] = source
            
            if value is None:
                alerts.append(f"{field_name} not found")
        
        fields_found = sum(1 for k in FIELD_LABELS if result.get(k) is not None)
        result['fields_extracted'] = fields_found
        result['confidence'] = 'high' if fields_found >= 4 else 'medium' if fields_found >= 2 else 'low'
        result['extraction_method'] = 'enhanced_regex_robust_rbl_fixed'
        result['alerts'] = alerts
        result['has_warnings'] = len(alerts) > 0
        
        with open(f"outputs/{self.base_name}_debug.log", "w", encoding="utf-8") as f:
            f.write("\n".join(self.debug_log))
        
        return result

def parse_with_regex(pdf_path: str) -> Dict[str, Any]:
    parser = CCStatementParser(pdf_path)
    result = parser.extract()
    
    os.makedirs("outputs", exist_ok=True)
    with open(f"outputs/{Path(pdf_path).stem}_parsed.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    
    return result

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("\nUsage: python parser.py <pdf_file>")
        sys.exit(1)
    
    result = parse_with_regex(sys.argv[1])
    print(json.dumps(result, indent=2))