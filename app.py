import streamlit as st
import json
import os
from pathlib import Path
from parser import parse_with_regex
from llm_extractor import extract_with_llm
import config

# Page configuration
st.set_page_config(
    page_title="Credit Card Statement Parser",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS with proper dark mode support
st.markdown("""
<style>
    /* Compact layout */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 1rem;
    }
    
    /* Compact headers */
    h1 {
        font-size: 1.8rem !important;
        font-weight: 600 !important;
        margin-bottom: 0.5rem !important;
    }
    
    h2 {
        font-size: 1.3rem !important;
        font-weight: 600 !important;
        margin-top: 1rem !important;
    }
    
    h3 {
        font-size: 1.1rem !important;
        font-weight: 500 !important;
    }
    
    /* Compact metrics */
    [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
    }
    
    /* Success box - readable in both themes */
    .success-box {
        padding: 0.7rem 1rem;
        border-radius: 4px;
        background-color: #d4edda;
        color: #155724;
        border-left: 4px solid #28a745;
        margin: 0.8rem 0;
        font-weight: 500;
    }
    
    /* Warning box - readable in both themes */
    .warning-box {
        padding: 0.7rem 1rem;
        border-radius: 4px;
        background-color: #fff3cd;
        color: #856404;
        border-left: 4px solid #ffc107;
        margin: 0.8rem 0;
        font-weight: 500;
    }
    
    /* Error box - readable in both themes */
    .error-box {
        padding: 0.7rem 1rem;
        border-radius: 4px;
        background-color: #f8d7da;
        color: #721c24;
        border-left: 4px solid #dc3545;
        margin: 0.8rem 0;
        font-weight: 500;
    }
    
    /* Compact info boxes */
    .stAlert {
        padding: 0.5rem 1rem !important;
        font-size: 0.9rem !important;
    }
    
    /* Clean buttons */
    .stButton button {
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        padding: 0.4rem 1.5rem !important;
    }
    
    /* Remove excessive spacing */
    .element-container {
        margin-bottom: 0.5rem !important;
    }
    
    /* Sidebar text color fix */
    [data-testid="stSidebar"] {
        background-color: transparent !important;
    }
    
    [data-testid="stSidebar"] * {
        color: inherit !important;
    }
    
    /* Make sure all text is readable */
    [data-testid="stMarkdown"] p {
        color: inherit !important;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("Credit Card Statement Parser")
st.markdown("**Extract key financial data from credit card statements**")
st.markdown("---")

# Sidebar - Settings
with st.sidebar:
    st.header("Settings")
    
    # Extraction method
    extraction_mode = st.radio(
        "Extraction Method",
        ["Regex (Fast)", "AI/LLM (Advanced)"],
        help="Regex: Fast pattern matching | AI: Intelligent extraction"
    )
    
    # LLM settings (only if AI mode selected)
    if extraction_mode == "AI/LLM (Advanced)":
        st.markdown("### AI Configuration")
        llm_provider = st.selectbox(
            "Provider",
            ["groq", "gemini"],
            help="Groq: Fast & Free | Gemini: High accuracy"
        )
        
        # API key input
        api_key_label = "Groq API Key" if llm_provider == "groq" else "Gemini API Key"
        api_key = st.text_input(
            api_key_label,
            type="password",
            value=config.GROQ_API_KEY if llm_provider == "groq" else config.GEMINI_API_KEY,
            help="Enter your API key"
        )
        
        if api_key:
            os.environ[f"{llm_provider.upper()}_API_KEY"] = api_key
    else:
        llm_provider = None
    
    st.markdown("---")
    
    # Info section
    st.markdown("### Extracted Fields")
    st.markdown("""
    - Card Last 4 Digits
    - Statement Period
    - Payment Due Date
    - Total Amount Due
    - Credit Limit
    """)
    
    st.markdown("---")
    st.caption("v1.0 | Production Build")

# Main Content Area
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Select Statement")
    
    # Statement selection
    statement_options = ["Custom Upload"] + list(config.SAMPLE_STATEMENTS.keys())
    selected_statement = st.selectbox(
        "Choose a statement",
        statement_options,
        label_visibility="collapsed"
    )

with col2:
    # Upload button
    if selected_statement == "Custom Upload":
        uploaded_file = st.file_uploader(
            "Upload PDF",
            type=['pdf'],
            label_visibility="collapsed"
        )
    else:
        uploaded_file = None

# Determine file to process
if selected_statement != "Custom Upload":
    pdf_path = config.SAMPLE_STATEMENTS.get(selected_statement)
    if pdf_path and Path(pdf_path).exists():
        pdf_to_process = pdf_path
        st.info(f"📌 Selected: {selected_statement}")
    else:
        st.warning(f"⚠️ Sample file not found: {pdf_path}")
        pdf_to_process = None
else:
    if uploaded_file:
        temp_path = "temp_uploaded.pdf"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())
        pdf_to_process = temp_path
        st.success(f"✓ Uploaded: {uploaded_file.name}")
    else:
        pdf_to_process = None

st.markdown("---")

# Extract button
if pdf_to_process:
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        extract_label = "🔍 Extract with Regex" if extraction_mode == "Regex (Fast)" else "🤖 Extract with AI"
        extract_btn = st.button(extract_label, type="primary", use_container_width=True)
    
    if extract_btn:
        # Show processing status
        status_msg = "Processing with regex..." if extraction_mode == "Regex (Fast)" else f"Processing with {llm_provider.upper()}..."
        
        with st.spinner(status_msg):
            try:
                # Extract
                if extraction_mode == "Regex (Fast)":
                    result = parse_with_regex(pdf_to_process)
                else:
                    # Validate API key
                    if llm_provider == "groq" and not os.getenv("GROQ_API_KEY"):
                        st.error("❌ Groq API key required")
                        st.stop()
                    elif llm_provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
                        st.error("❌ Gemini API key required")
                        st.stop()
                    
                    result = extract_with_llm(pdf_to_process, llm_provider)
                
                # Confidence badge with proper colors
                conf = result['confidence']
                fields = result['fields_extracted']
                method = result['extraction_method']
                
                if conf == 'high':
                    st.markdown(
                        f'<div class="success-box">✓ HIGH CONFIDENCE ({fields}/5 fields) | Method: {method}</div>', 
                        unsafe_allow_html=True
                    )
                elif conf == 'medium':
                    st.markdown(
                        f'<div class="warning-box">⚠ MEDIUM CONFIDENCE ({fields}/5 fields) | Method: {method}</div>', 
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="error-box">✗ LOW CONFIDENCE ({fields}/5 fields) | Method: {method}</div>', 
                        unsafe_allow_html=True
                    )
                
                st.markdown("---")
                
                # Results display - Compact layout
                st.subheader("Extracted Data")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    card = result.get('card_last_4')
                    st.metric("💳 Card Last 4", f"****{card}" if card else "Not Found")
                    
                    period = result.get('statement_period')
                    display_period = (period[:20] + "...") if period and len(period) > 20 else (period or "Not Found")
                    st.metric("📊 Statement Period", display_period)
                
                with col2:
                    due = result.get('due_date')
                    st.metric("📅 Due Date", due if due else "Not Found")
                    
                    amount = result.get('amount_due')
                    if amount:
                        st.metric("💰 Amount Due", f"₹{amount:,.2f}")
                    else:
                        st.metric("💰 Amount Due", "Not Found")
                
                with col3:
                    limit = result.get('credit_limit')
                    if limit:
                        st.metric("🎯 Credit Limit", f"₹{limit:,.2f}")
                    else:
                        st.metric("🎯 Credit Limit", "Not Found")
                
                # Alerts section
                if result.get('has_warnings'):
                    st.markdown("---")
                    with st.expander("⚠️ Alerts & Warnings", expanded=False):
                        for alert in result['alerts']:
                            st.warning(alert, icon="⚠️")
                
                st.markdown("---")
                
                # Actions
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    json_str = json.dumps(result, indent=2)
                    st.download_button(
                        "📥 Download JSON",
                        json_str,
                        file_name=f"extracted_{Path(pdf_to_process).stem}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                with col2:
                    base_name = Path(pdf_to_process).stem
                    raw_text_file = config.OUTPUT_DIR / f"{base_name}_raw_text.txt"
                    if raw_text_file.exists():
                        with open(raw_text_file, 'r', encoding='utf-8') as f:
                            raw_text = f.read()
                        st.download_button(
                            "📄 Download Raw Text",
                            raw_text,
                            file_name=f"{base_name}_raw_text.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                
                with col3:
                    with st.expander("📋 View JSON"):
                        st.json(result)
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                with st.expander("Error Details"):
                    st.exception(e)
        
        # Cleanup
        if selected_statement == "Custom Upload" and os.path.exists("temp_uploaded.pdf"):
            try:
                os.remove("temp_uploaded.pdf")
            except:
                pass

else:
    st.info("👆 Please select a sample statement or upload a PDF to begin")
    
    # Example output
    with st.expander("📖 Example Output Preview"):
        example = {
            "card_last_4": "7381",
            "statement_period": "17/09/2021 - 15/10/2021",
            "due_date": "04/11/2021",
            "amount_due": 78708.38,
            "credit_limit": 132000.0,
            "confidence": "high",
            "fields_extracted": 5,
            "extraction_method": "regex_enhanced"
        }
        st.json(example)

# Footer
st.markdown("---")
st.caption("Supports Axis, IDFC, ICICI, HDFC, RBL and other major banks | Built with Streamlit")
