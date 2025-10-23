import streamlit as st
import json
import os
from pathlib import Path
from parser import parse_with_regex
from llm_extractor import extract_with_llm
import config

# Page setup
st.set_page_config(
    page_title="CC Statement Parser",
    page_icon="💳",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .extraction-type {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .regex-mode {
        background-color: #e3f2fd;
        border-left: 4px solid #2196F3;
    }
    .llm-mode {
        background-color: #f3e5f5;
        border-left: 4px solid #9C27B0;
    }
</style>
""", unsafe_allow_html=True)

st.title("💳 Credit Card Statement Parser")
st.markdown("Extract key data from credit card statements using **Regex** or **AI**")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Extraction method selection
    st.markdown("### Extraction Method")
    extraction_mode = st.radio(
        "Choose extraction method:",
        ["Regex (Fast)", "AI / LLM (Advanced)"],
        help="Regex: Pattern matching (instant)\nAI: LLM-based (requires API key)"
    )
    
    # LLM provider selection (only if LLM mode)
    if extraction_mode == "AI / LLM (Advanced)":
        st.markdown("### AI Provider")
        llm_provider = st.selectbox(
            "Select AI provider:",
            ["groq", "gemini"],
            help="Groq: Free & Fast (500+ tokens/sec)\nGemini: Accurate ($0.075/1M tokens)"
        )
        
        # API key input
        if llm_provider == "groq":
            api_key = st.text_input(
                "Groq API Key",
                type="password",
                value=config.GROQ_API_KEY,
                help="Get free key: https://console.groq.com"
            )
            if api_key:
                os.environ["GROQ_API_KEY"] = api_key
        else:
            api_key = st.text_input(
                "Gemini API Key",
                type="password",
                value=config.GEMINI_API_KEY,
                help="Get key: https://ai.google.dev"
            )
            if api_key:
                os.environ["GEMINI_API_KEY"] = api_key
    else:
        llm_provider = None
    
    st.markdown("---")
    
    st.markdown("### 📋 Extracted Fields")
    st.markdown("""
    1. Card Last 4 Digits
    2. Statement Period
    3. Payment Due Date
    4. Total Amount Due
    5. Credit Limit
    """)
    
    st.markdown("---")
    
    st.markdown("### 📊 Method Comparison")
    st.markdown("""
    **Regex:**
    - ⚡ Instant (< 1s)
    - 🆓 Free
    - 🎯 Works on standard formats
    
    **AI/LLM:**
    - 🤖 Intelligent extraction
    - ⏱️ 1-2 seconds
    - 🔍 Handles unusual formats
    """)

# Main content
st.markdown("---")

# PDF selection
st.markdown("### 📄 Select Statement")

col1, col2 = st.columns([2, 1])

with col1:
    # Dropdown for sample statements
    statement_options = ["Custom Upload"] + list(config.SAMPLE_STATEMENTS.keys())
    selected_statement = st.selectbox(
        "Choose from samples or upload custom:",
        statement_options,
        help="Select a pre-loaded sample or choose 'Custom Upload' to use your own PDF"
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    # Custom upload (only show if Custom Upload is selected)
    if selected_statement == "Custom Upload":
        uploaded_file = st.file_uploader(
            "Upload PDF",
            type=['pdf'],
            help="Upload your credit card statement"
        )
    else:
        uploaded_file = None

# Determine which file to process
if selected_statement != "Custom Upload":
    # Use sample statement
    pdf_path = config.SAMPLE_STATEMENTS.get(selected_statement)
    if pdf_path and Path(pdf_path).exists():
        pdf_to_process = pdf_path
        st.info(f"📌 Selected: {selected_statement}")
    else:
        st.warning(f"⚠️ Sample file not found: {pdf_path}")
        st.info("💡 Place your sample PDFs in the `sample_statements/` folder")
        pdf_to_process = None
else:
    # Use uploaded file
    if uploaded_file:
        temp_path = "temp_uploaded.pdf"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())
        pdf_to_process = temp_path
        st.success(f"✅ Uploaded: {uploaded_file.name}")
    else:
        pdf_to_process = None

# Extract button
st.markdown("---")

if pdf_to_process:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if extraction_mode == "Regex (Fast)":
            extract_btn = st.button(
                "🔍 Extract with Regex",
                type="primary",
                use_container_width=True
            )
        else:
            extract_btn = st.button(
                "🤖 Extract with AI",
                type="primary",
                use_container_width=True
            )
    
    if extract_btn:
        # Show extraction mode
        if extraction_mode == "Regex (Fast)":
            st.markdown('<div class="extraction-type regex-mode">⚡ <b>Using Regex Extraction</b></div>', 
                       unsafe_allow_html=True)
            status_msg = "Extracting with regex patterns..."
        else:
            st.markdown(f'<div class="extraction-type llm-mode">🤖 <b>Using AI Extraction ({llm_provider.upper()})</b></div>', 
                       unsafe_allow_html=True)
            status_msg = f"Extracting with {llm_provider.upper()} AI..."
        
        with st.spinner(status_msg):
            try:
                # Extract based on mode
                if extraction_mode == "Regex (Fast)":
                    result = parse_with_regex(pdf_to_process)
                else:
                    # Check API key
                    if llm_provider == "groq" and not os.getenv("GROQ_API_KEY"):
                        st.error("❌ Groq API key not set!")
                        st.stop()
                    elif llm_provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
                        st.error("❌ Gemini API key not set!")
                        st.stop()
                    
                    result = extract_with_llm(pdf_to_process, llm_provider)
                
                # Display confidence
                conf = result['confidence']
                method = result['extraction_method']
                fields = result['fields_extracted']
                
                if conf == 'high':
                    st.success(f"✅ {conf.upper()} confidence ({fields}/5 fields) | Method: {method}")
                elif conf == 'medium':
                    st.warning(f"⚠️ {conf.upper()} confidence ({fields}/5 fields) | Method: {method}")
                else:
                    st.error(f"❌ {conf.upper()} confidence ({fields}/5 fields) | Method: {method}")
                
                st.markdown("---")
                
                # Display results in cards
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    card = result.get('card_last_4')
                    st.metric("💳 Card Last 4", f"****{card}" if card else "❌ Not Found")
                    
                    due = result.get('due_date')
                    st.metric("📅 Due Date", due if due else "❌ Not Found")
                
                with col2:
                    period = result.get('statement_period')
                    display_period = (period[:25] + "...") if period and len(period) > 25 else (period or "❌ Not Found")
                    st.metric("📊 Statement Period", display_period)
                    
                    amount = result.get('amount_due')
                    if amount:
                        st.metric("💰 Amount Due", f"₹{amount:,.2f}")
                    else:
                        st.metric("💰 Amount Due", "❌ Not Found")
                
                with col3:
                    limit = result.get('credit_limit')
                    if limit:
                        st.metric("🎯 Credit Limit", f"₹{limit:,.2f}")
                    else:
                        st.metric("🎯 Credit Limit", "❌ Not Found")
                
                st.markdown("---")
                
                # JSON output
                with st.expander("📄 View Complete JSON"):
                    st.json(result)
                
                # Download
                col1, col2 = st.columns(2)
                
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
                    # Save to outputs
                    output_file = config.OUTPUT_DIR / f"extracted_{Path(pdf_to_process).stem}.json"
                    with open(output_file, 'w') as f:
                        json.dump(result, f, indent=2)
                    st.success(f"💾 Saved to outputs/")
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                with st.expander("Error Details"):
                    st.exception(e)
        
        # Cleanup temp file
        if selected_statement == "Custom Upload" and os.path.exists("temp_uploaded.pdf"):
            try:
                os.remove("temp_uploaded.pdf")
            except:
                pass

else:
    st.info("👆 Select a sample statement or upload your own PDF")
    
    # Example output
    st.markdown("### 📖 Example Output")
    example = {
        "card_last_4": "7381",
        "statement_period": "17/09/2021 - 15/10/2021",
        "due_date": "04/11/2021",
        "amount_due": 78708.38,
        "credit_limit": 132000.0,
        "confidence": "high",
        "fields_extracted": 5,
        "extraction_method": "regex"
    }
    st.json(example)

# Footer
st.markdown("---")
st.caption("Built with Regex + AI • Toggle between fast pattern matching and intelligent LLM extraction")
