#!/usr/bin/env python3
"""
Auris - Films & Series Intelligence Agent
Web Interface
"""

import os
import io
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from integrations.data_loader import DataLoader
from integrations.trello import TrelloIntegration
from integrations.industry import IndustryIntelligence
from integrations.portfolio import PortfolioIntegration
from integrations.pdf_parser import PDFParser
from integrations.imdb_pro import IMDbProSync

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Auris",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load SVG logo
def get_logo_svg():
    logo_path = Path(__file__).parent / "Auris_logo_2.svg"
    if logo_path.exists():
        return logo_path.read_text()
    return ""

LOGO_SVG = get_logo_svg()

# Custom CSS for the dark minimal aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&display=swap');
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Main app background */
    .stApp {
        background: radial-gradient(ellipse at center, #0a1628 0%, #050a12 50%, #020408 100%);
        min-height: 100vh;
    }
    
    /* Remove default padding */
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        max-width: 100% !important;
    }
    
    /* Center container */
    .center-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
        padding: 2rem;
    }
    
    /* Logo styling */
    .logo-container {
        width: 320px;
        margin-bottom: 3rem;
        opacity: 0.95;
    }
    
    .logo-container svg {
        width: 100%;
        height: auto;
    }
    
    /* Input container */
    .input-wrapper {
        width: 100%;
        max-width: 480px;
        position: relative;
    }
    
    /* Style the chat input */
    .stChatInput {
        background: transparent !important;
    }
    
    .stChatInput > div {
        background: transparent !important;
    }
    
    .stChatInput textarea {
        background: rgba(255, 255, 255, 0.95) !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 16px 50px 16px 20px !important;
        font-family: 'Cormorant Garamond', Georgia, serif !important;
        font-size: 16px !important;
        color: #1a1a2e !important;
        letter-spacing: 0.15em !important;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3) !important;
    }
    
    .stChatInput textarea::placeholder {
        color: #666 !important;
        letter-spacing: 0.15em !important;
        font-family: 'Cormorant Garamond', Georgia, serif !important;
    }
    
    .stChatInput button {
        background: transparent !important;
        border: none !important;
        color: #3a5a6a !important;
    }
    
    /* Chat messages */
    .stChatMessage {
        background: transparent !important;
        border: none !important;
    }
    
    .stChatMessage [data-testid="stMarkdownContainer"] {
        color: rgba(255, 255, 255, 0.9) !important;
        font-family: 'Cormorant Garamond', Georgia, serif !important;
        font-size: 17px !important;
        line-height: 1.7 !important;
        letter-spacing: 0.02em !important;
    }
    
    /* User message styling */
    [data-testid="stChatMessageContent-user"] {
        background: rgba(60, 80, 100, 0.3) !important;
        border-radius: 8px !important;
        padding: 1rem 1.5rem !important;
    }
    
    /* Assistant message styling */
    [data-testid="stChatMessageContent-assistant"] {
        background: rgba(30, 40, 60, 0.4) !important;
        border-radius: 8px !important;
        padding: 1rem 1.5rem !important;
        border-left: 2px solid rgba(106, 138, 122, 0.5) !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a1628 0%, #050a12 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: rgba(255, 255, 255, 0.7) !important;
        font-family: 'Cormorant Garamond', Georgia, serif !important;
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: rgba(255, 255, 255, 0.9) !important;
        font-family: 'Cormorant Garamond', Georgia, serif !important;
        font-weight: 300 !important;
        letter-spacing: 0.1em !important;
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px dashed rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }
    
    [data-testid="stFileUploader"] label {
        color: rgba(255, 255, 255, 0.6) !important;
        font-family: 'Cormorant Garamond', Georgia, serif !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: rgba(255, 255, 255, 0.05) !important;
        color: rgba(255, 255, 255, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 4px !important;
        font-family: 'Cormorant Garamond', Georgia, serif !important;
        letter-spacing: 0.1em !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.03) !important;
        border-radius: 4px !important;
        color: rgba(255, 255, 255, 0.7) !important;
        font-family: 'Cormorant Garamond', Georgia, serif !important;
    }
    
    /* Success/warning messages */
    .stSuccess, .stWarning, .stError {
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 4px !important;
        font-family: 'Cormorant Garamond', Georgia, serif !important;
    }
    
    /* Metrics */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border-radius: 8px !important;
        padding: 1rem !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: rgba(255, 255, 255, 0.5) !important;
        font-family: 'Cormorant Garamond', Georgia, serif !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        font-size: 12px !important;
    }
    
    [data-testid="stMetricValue"] {
        color: rgba(138, 165, 197, 0.9) !important;
        font-family: 'Cormorant Garamond', Georgia, serif !important;
        font-weight: 300 !important;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-color: rgba(106, 138, 122, 0.5) transparent transparent !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.2);
    }
    
    /* Status indicators */
    .status-dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-loaded {
        background: rgba(106, 138, 122, 0.8);
        box-shadow: 0 0 8px rgba(106, 138, 122, 0.4);
    }
    
    .status-pending {
        background: rgba(197, 165, 165, 0.6);
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "data_loader" not in st.session_state:
        st.session_state.data_loader = DataLoader()
    if "trello" not in st.session_state:
        st.session_state.trello = TrelloIntegration()
    if "industry" not in st.session_state:
        st.session_state.industry = IndustryIntelligence()
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = PortfolioIntegration()
    if "pdf_parser" not in st.session_state:
        st.session_state.pdf_parser = PDFParser()
    if "imdb_pro" not in st.session_state:
        st.session_state.imdb_pro = IMDbProSync()
    if "uploaded_data" not in st.session_state:
        st.session_state.uploaded_data = {
            "revenue_goals": None,
            "weekly_pnl": None,
            "clients": None,
            "reports": []
        }


def get_ai_client():
    """Get the appropriate AI client."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if anthropic_key and anthropic_key.startswith("sk-ant-"):
        from anthropic import Anthropic
        return Anthropic(api_key=anthropic_key), "anthropic"
    elif openai_key and openai_key.startswith("sk-"):
        from openai import OpenAI
        return OpenAI(api_key=openai_key), "openai"
    else:
        return None, None


def build_system_prompt():
    """Build the system prompt with current data context."""
    today = datetime.now().strftime("%B %d, %Y")
    
    data_loader = st.session_state.data_loader
    uploaded = st.session_state.uploaded_data
    
    if uploaded["revenue_goals"] is not None:
        data_loader.revenue_goals = uploaded["revenue_goals"]
    if uploaded["weekly_pnl"] is not None:
        data_loader.weekly_pnl = uploaded["weekly_pnl"]
    if uploaded["clients"] is not None:
        data_loader.clients = uploaded["clients"]
    
    revenue_context = data_loader.format_revenue_summary()
    pnl_context = data_loader.format_pnl_summary()
    client_context = data_loader.format_client_summary()
    project_context = st.session_state.trello.format_project_summary()
    
    report_context = ""
    if uploaded["reports"]:
        report_context = "\n\n## Uploaded Reports\n"
        for report in uploaded["reports"]:
            report_context += f"\n### {report['filename']}\n{report['content'][:3000]}...\n"
    
    imdb_context = ""
    if st.session_state.imdb_pro.is_configured:
        imdb_context = "\n\n## IMDb Pro\nIMDb Pro integration is configured. You can search for projects, people, upcoming releases, and projects in development. Use these capabilities to provide industry intelligence."
    
    return f"""You are Auris, an AI assistant for the Head of Films & Series at Create Advertising (createadvertising.com).

Today's date: {today}

Your role is to help with:
1. Tracking creative director performance against sales targets
2. Monitoring active job P&L and profitability
3. Identifying business development opportunities
4. Understanding industry trends and upcoming projects
5. Leveraging recent work for new business pitches

CURRENT DATA CONTEXT:

## Creative Director Revenue Goals (2026)
{revenue_context}

## Active Jobs P&L Summary
{pnl_context}

## Top Clients
{client_context}

## Current Projects (from Trello)
{project_context}
{report_context}
{imdb_context}

GUIDELINES:
- Be direct and actionable in your responses
- When discussing performance, always reference specific numbers
- When suggesting outreach opportunities, be specific about which work to reference
- For industry questions, note if you need to fetch fresh data
- Always consider both revenue AND margin when evaluating performance
- Flag any jobs that are over budget or behind schedule
- Use bullet points and clear formatting for readability
- Maintain a sophisticated, professional tone

If data is not available for a question, clearly state what data is missing and how it can be provided."""


def get_ai_response(user_message: str) -> str:
    """Get a response from the AI model."""
    client, provider = get_ai_client()
    
    if client is None:
        return "No API key configured. Please add your OpenAI or Anthropic API key to the .env file."
    
    messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    messages.append({"role": "user", "content": user_message})
    
    system_prompt = build_system_prompt()
    
    try:
        if provider == "anthropic":
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_prompt,
                messages=messages
            )
            return response.content[0].text
        else:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=full_messages,
                max_tokens=4096
            )
            return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"


def process_csv_upload(uploaded_file, data_type: str):
    """Process an uploaded CSV file."""
    try:
        df = pd.read_csv(uploaded_file, comment='#')
        if df.empty:
            st.warning(f"The {data_type} file appears to be empty.")
            return None
        st.session_state.uploaded_data[data_type] = df
        return df
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return None


def process_pdf_upload(uploaded_file):
    """Process an uploaded PDF file."""
    try:
        content = st.session_state.pdf_parser.parse_pdf(uploaded_file)
        report_data = {
            "filename": uploaded_file.name,
            "content": content,
            "uploaded_at": datetime.now().isoformat()
        }
        st.session_state.uploaded_data["reports"].append(report_data)
        return content
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None


def render_sidebar():
    """Render the sidebar with data upload and status."""
    with st.sidebar:
        st.markdown("### Data Sources")
        
        uploaded = st.session_state.uploaded_data
        
        for name, key in [("Revenue Goals", "revenue_goals"), ("Weekly P&L", "weekly_pnl"), ("Clients", "clients")]:
            loaded = uploaded[key] is not None
            dot_class = "status-loaded" if loaded else "status-pending"
            status_text = "Loaded" if loaded else "Pending"
            st.markdown(f'<span class="status-dot {dot_class}"></span>{name}: {status_text}', unsafe_allow_html=True)
        
        report_count = len(uploaded["reports"])
        dot_class = "status-loaded" if report_count > 0 else "status-pending"
        st.markdown(f'<span class="status-dot {dot_class}"></span>Reports: {report_count} loaded', unsafe_allow_html=True)
        
        trello_status = "Connected" if st.session_state.trello.is_configured else "Not configured"
        dot_class = "status-loaded" if st.session_state.trello.is_configured else "status-pending"
        st.markdown(f'<span class="status-dot {dot_class}"></span>Trello: {trello_status}', unsafe_allow_html=True)
        
        imdb_status = "Configured" if st.session_state.imdb_pro.is_configured else "Not configured"
        dot_class = "status-loaded" if st.session_state.imdb_pro.is_configured else "status-pending"
        st.markdown(f'<span class="status-dot {dot_class}"></span>IMDb Pro: {imdb_status}', unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### Upload")
        
        with st.expander("Revenue Goals"):
            revenue_file = st.file_uploader("CSV", type=["csv"], key="revenue_upload", label_visibility="collapsed")
            if revenue_file:
                df = process_csv_upload(revenue_file, "revenue_goals")
                if df is not None:
                    st.success(f"{len(df)} directors")
        
        with st.expander("Weekly P&L"):
            pnl_file = st.file_uploader("CSV", type=["csv"], key="pnl_upload", label_visibility="collapsed")
            if pnl_file:
                df = process_csv_upload(pnl_file, "weekly_pnl")
                if df is not None:
                    st.success(f"{len(df)} jobs")
        
        with st.expander("Clients"):
            clients_file = st.file_uploader("CSV", type=["csv"], key="clients_upload", label_visibility="collapsed")
            if clients_file:
                df = process_csv_upload(clients_file, "clients")
                if df is not None:
                    st.success(f"{len(df)} clients")
        
        with st.expander("Reports"):
            pdf_files = st.file_uploader("PDF", type=["pdf"], key="pdf_upload", accept_multiple_files=True, label_visibility="collapsed")
            if pdf_files:
                for pdf_file in pdf_files:
                    existing_names = [r["filename"] for r in uploaded["reports"]]
                    if pdf_file.name not in existing_names:
                        content = process_pdf_upload(pdf_file)
                        if content:
                            st.success(f"{pdf_file.name}")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Refresh", use_container_width=True):
                projects = st.session_state.trello.get_projects()
                st.success(f"{len(projects)} projects")
        with col2:
            if st.button("Clear", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        if st.session_state.imdb_pro.is_configured:
            st.markdown("---")
            st.markdown("### IMDb Pro")
            if st.button("Test IMDb Pro Login", use_container_width=True):
                with st.spinner("Logging in..."):
                    success = st.session_state.imdb_pro.login()
                if success:
                    st.success("Connected to IMDb Pro")
                else:
                    st.error("Login failed")


def render_main():
    """Render the main chat interface."""
    has_messages = len(st.session_state.messages) > 0
    
    if has_messages:
        st.markdown(f"""
        <div style="text-align: center; padding: 1.5rem 0;">
            <div style="width: 140px; margin: 0 auto; opacity: 0.9;">
                {LOGO_SVG}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    else:
        st.markdown(f"""
        <div class="center-container">
            <div class="logo-container">
                {LOGO_SVG}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    if prompt := st.chat_input(""):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner(""):
                response = get_ai_response(prompt)
            st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()


def main():
    """Main application."""
    init_session_state()
    render_sidebar()
    render_main()


if __name__ == "__main__":
    main()

