import os
import sys

# Suppress heavy backend logging and oneDNN checks
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import tempfile
from pathlib import Path
from PIL import Image
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

st.set_page_config(
    page_title="VeriTrace",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap');

    :root {
        --bg-deep: #03140D;
        --bg-primary: #06261A;
        --bg-card: #0A3323;
        --bg-card-alt: #0F3F2D;
        --bg-card-hover: #144C36;
        --bg-muted: #072217;
        --accent-gold: #F5D400;
        --accent-gold-glow: rgba(245, 212, 0, 0.45);
        --accent-gold-dim: rgba(245, 212, 0, 0.12);
        --accent-pink: #EC1E79;
        --accent-pink-glow: rgba(236, 30, 121, 0.45);
        --accent-pink-dim: rgba(236, 30, 121, 0.15);
        --accent-alert: #FF2E5B;
        --accent-alert-dim: rgba(255, 46, 91, 0.18);
        --text-light: #F8F6EE;
        --text-muted: #A3C6B6;
        --text-dark: #041C13;
        --border-green: rgba(36, 115, 82, 0.75);
        --border-gold: rgba(245, 212, 0, 0.45);
        --border-dark: #07150F;
        --shadow-poster: 4px 4px 0px #020C08;
    }

    /* ── Global Background & Atmospheric Screen-Print ── */
    .stApp, [data-testid="stAppViewContainer"] {
        background: 
            radial-gradient(ellipse at 88% 12%, rgba(18, 76, 52, 0.75) 0%, transparent 55%),
            radial-gradient(ellipse at 12% 88%, rgba(10, 52, 36, 0.85) 0%, transparent 60%),
            linear-gradient(168deg, #07291C 0%, #03140D 100%) !important;
        color: var(--text-light) !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Screen-Print Micro-Grid Overlay */
    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        inset: 0;
        background-image: 
            radial-gradient(rgba(245, 212, 0, 0.045) 1px, transparent 1px),
            linear-gradient(rgba(245, 212, 0, 0.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(245, 212, 0, 0.02) 1px, transparent 1px);
        background-size: 26px 26px, 52px 52px, 52px 52px;
        pointer-events: none;
        z-index: 0;
    }

    /* ── Sidebar: Dark Jungle Panel ── */
    [data-testid="stSidebar"] {
        background: #041B12 !important;
        border-right: 3px solid var(--border-dark) !important;
        box-shadow: 6px 0 20px rgba(0, 0, 0, 0.45) !important;
    }

    [data-testid="stSidebar"] * {
        color: var(--text-light) !important;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] [data-testid="stSubheader"] {
        font-family: 'DM Serif Display', serif !important;
        color: var(--accent-gold) !important;
        font-size: 1.25rem !important;
        letter-spacing: 0.8px !important;
        border-bottom: 2px solid var(--border-gold) !important;
        padding-bottom: 6px !important;
        margin-top: 1.3rem !important;
        margin-bottom: 0.9rem !important;
        text-shadow: 1px 1px 0px var(--border-dark);
    }

    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stTextInput label {
        font-family: 'Space Mono', monospace !important;
        text-transform: uppercase !important;
        letter-spacing: 1.2px !important;
        font-size: 0.75rem !important; /* Min floor >= 11px */
        font-weight: 700 !important;
        color: var(--accent-gold) !important;
        margin-bottom: 4px !important;
    }

    /* ── Main Typography ── */
    h1, h2, h3,
    [data-testid="stSubheader"],
    .stSubheader {
        font-family: 'DM Serif Display', serif !important;
        color: var(--accent-gold) !important;
        letter-spacing: 0.5px !important;
        line-height: 1.2 !important;
    }

    .stMarkdown p, .stMarkdown li, .stMarkdown td, .stMarkdown th,
    .stText, p, li {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: var(--text-light) !important;
        font-size: 0.9rem !important;
        line-height: 1.6 !important;
        word-break: normal !important;
        overflow-wrap: break-word !important;
    }

    .stCaption, caption {
        font-family: 'Space Mono', monospace !important;
        color: var(--text-muted) !important;
        font-size: 0.75rem !important; /* Minimum 11px floor */
    }

    code {
        background-color: #020C08 !important;
        color: var(--accent-gold) !important;
        font-family: 'Space Mono', monospace !important;
        padding: 3px 8px !important;
        border-radius: 4px !important;
        font-size: 0.82rem !important;
        border: 1.5px solid var(--border-green) !important;
    }

    strong, b {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* ── High-Impact Retro Poster Buttons with Micro-Interactions & 44px min touch target ── */
    .stButton > button {
        background: var(--accent-gold) !important;
        color: var(--text-dark) !important;
        border: 2px solid var(--border-dark) !important;
        border-radius: 5px !important;
        font-family: 'Space Mono', monospace !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        font-size: 0.85rem !important;
        min-height: 44px !important; /* Accessibility minimum 44px touch target */
        padding: 0.65rem 1.6rem !important;
        box-shadow: var(--shadow-poster) !important;
        transition: transform 0.15s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.15s ease, background 0.15s ease !important;
    }

    .stButton > button:hover {
        background: #FFE033 !important;
        color: var(--text-dark) !important;
        box-shadow: 6px 6px 0px var(--border-dark), 0 0 22px var(--accent-gold-glow) !important;
        transform: translate(-2px, -2px) !important;
    }

    .stButton > button:active {
        box-shadow: 1px 1px 0px var(--border-dark) !important;
        transform: translate(2px, 2px) !important;
    }

    .stDownloadButton > button {
        background: var(--accent-gold) !important;
        color: var(--text-dark) !important;
        border: 2px solid var(--border-dark) !important;
        border-radius: 5px !important;
        font-family: 'Space Mono', monospace !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1.2px !important;
        font-size: 0.8rem !important;
        min-height: 44px !important;
        padding: 0.55rem 1.4rem !important;
        box-shadow: var(--shadow-poster) !important;
        transition: all 0.15s ease !important;
    }

    .stDownloadButton > button:hover {
        background: #FFE033 !important;
        box-shadow: 6px 6px 0px var(--border-dark), 0 0 18px var(--accent-gold-glow) !important;
        transform: translate(-2px, -2px) !important;
    }

    /* ── Form Inputs ── */
    .stTextInput input,
    [data-testid="stTextInput"] input,
    .stTextInput > div > div > input {
        background-color: #041B12 !important;
        color: var(--text-light) !important;
        border: 1.5px solid var(--border-green) !important;
        border-radius: 4px !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 0.85rem !important;
        padding: 9px 12px !important;
    }

    .stTextInput > div > div > input:focus,
    [data-testid="stTextInput"] input:focus {
        border-color: var(--accent-gold) !important;
        box-shadow: 0 0 0 3px var(--accent-gold-dim) !important;
    }

    .stSelectbox > div > div {
        background-color: #041B12 !important;
        border: 1.5px solid var(--border-green) !important;
        border-radius: 4px !important;
        color: var(--text-light) !important;
        font-size: 0.85rem !important;
    }

    .stRadio label,
    .stCheckbox label {
        font-size: 0.88rem !important;
        color: var(--text-light) !important;
    }

    /* ── Restrained Glassmorphism on Overlays & Status Widgets ── */
    [data-testid="stStatusWidget"] {
        background: rgba(4, 27, 18, 0.75) !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        border: 1.5px solid var(--border-gold) !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        margin-bottom: 12px !important;
        box-shadow: var(--shadow-poster) !important;
    }

    [data-testid="stStatusWidget"] summary {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.88rem !important;
        font-weight: 700 !important;
        color: var(--accent-gold) !important;
        padding: 4px 0 !important;
    }

    [data-testid="stStatusWidget"] [data-testid="stMarkdownContainer"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.84rem !important;
        color: var(--text-muted) !important;
    }

    [data-testid="stExpander"] {
        background: rgba(6, 34, 23, 0.72) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1.5px solid var(--border-green) !important;
        border-radius: 8px !important;
        margin-top: 12px !important;
        box-shadow: var(--shadow-poster) !important;
    }

    .streamlit-expanderHeader,
    [data-testid="stExpander"] summary {
        font-family: 'Space Mono', monospace !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        color: var(--accent-gold) !important;
        background-color: transparent !important;
        padding: 11px 15px !important;
    }

    /* ── Progress Bar ── */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--accent-gold), #FFE033, var(--accent-pink)) !important;
        border-radius: 3px !important;
    }

    .stProgress > div > div {
        background-color: #041B12 !important;
        border: 1.5px solid var(--border-green) !important;
        border-radius: 4px !important;
        height: 12px !important;
    }

    /* ── JSON Viewer ── */
    .stJson, [data-testid="stJson"] {
        background-color: #020C08 !important;
        border: 1.5px solid var(--border-green) !important;
        border-radius: 6px !important;
        padding: 10px !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 0.82rem !important;
        box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.5) !important;
    }

    /* ── File Uploader ── */
    [data-testid="stFileUploader"] {
        background: linear-gradient(135deg, #093423 0%, #052115 100%) !important;
        border: 2px dashed var(--accent-gold) !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        margin-bottom: 1rem !important;
        box-shadow: var(--shadow-poster) !important;
    }

    [data-testid="stFileUploaderDropzone"] {
        background: transparent !important;
        border: none !important;
        padding: 0.4rem !important;
    }

    [data-testid="stFileUploaderDropzoneInstructions"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.84rem !important;
        color: var(--text-light) !important;
    }

    [data-testid="stFileUploaderDropzoneInstructions"] small {
        color: var(--text-muted) !important;
        font-size: 0.75rem !important;
    }

    [data-testid="stFileUploader"] button {
        background: var(--accent-gold) !important;
        color: var(--text-dark) !important;
        border: 2px solid var(--border-dark) !important;
        border-radius: 4px !important;
        font-family: 'Space Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 0.78rem !important;
        min-height: 40px !important;
        padding: 0.4rem 0.9rem !important;
        box-shadow: 2px 2px 0px var(--border-dark) !important;
    }

    /* ── Images ── */
    [data-testid="stImage"] img {
        border-radius: 6px !important;
        border: 2px solid var(--border-dark) !important;
        box-shadow: 3px 3px 0px var(--border-dark) !important;
    }

    /* ══════════════════════════════════════════════════════
       Bento Grid, Poster Patterns, Badges & Micro-Interactions
       ══════════════════════════════════════════════════════ */

    .header-bar {
        background: linear-gradient(135deg, #052317 0%, #0E412E 45%, #07261A 100%);
        border: 2px solid var(--border-dark);
        border-left: 8px solid var(--accent-gold);
        border-radius: 8px;
        padding: 1.6rem 2.2rem;
        margin-bottom: 1.8rem;
        box-shadow: 6px 6px 0px var(--border-dark), 0 0 28px rgba(0, 0, 0, 0.45);
        position: relative;
        overflow: hidden;
    }

    .header-bar::after {
        content: "REGISTRY";
        position: absolute;
        right: -10px;
        bottom: -15px;
        font-family: 'DM Serif Display', serif;
        font-size: 4.8rem;
        color: rgba(245, 212, 0, 0.04);
        letter-spacing: 6px;
        pointer-events: none;
        user-select: none;
    }

    .header-tag {
        display: inline-block;
        background: var(--accent-pink);
        color: #FFFFFF;
        font-family: 'Space Mono', monospace;
        font-weight: 700;
        font-size: 0.7rem; /* >= 11px floor */
        letter-spacing: 2px;
        text-transform: uppercase;
        padding: 3px 9px;
        border-radius: 3px;
        border: 1px solid var(--border-dark);
        margin-bottom: 8px;
        box-shadow: 2px 2px 0px var(--border-dark);
    }

    .app-title {
        font-family: 'DM Serif Display', serif;
        font-size: 3.4rem;
        font-weight: 700;
        color: var(--accent-gold);
        margin: 0;
        line-height: 1.05;
        text-shadow: 3px 3px 0px var(--border-dark);
        letter-spacing: 1.5px;
        transition: transform 0.2s ease;
    }

    .app-title:hover {
        transform: scale(1.01);
    }

    .app-subtitle {
        font-family: 'Space Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 2.2px;
        color: var(--text-muted);
        font-size: 0.8rem;
        margin-top: 6px;
        font-weight: 700;
    }

    /* Screen-Printed Repeating Pattern Divider (Rows 1-2) */
    .retro-pattern-divider {
        height: 14px;
        background-image: 
            radial-gradient(circle, #F5D400 2px, transparent 2.5px),
            radial-gradient(circle, #EC1E79 2px, transparent 2.5px);
        background-size: 20px 14px;
        background-position: 0 0, 10px 7px;
        opacity: 0.75;
        margin: 1.8rem 0;
    }

    /* Serious Thin Gold Line Divider (Row 3 Verification Gate) */
    .serious-gold-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--accent-gold), transparent);
        border: none;
        margin: 2.2rem 0;
        opacity: 0.7;
    }

    /* Bento Grid Card Containers (Solid, Tactile, Offset Poster Shadow) */
    .bento-card {
        background: linear-gradient(135deg, #0B3624 0%, #06261A 100%);
        border: 2px solid var(--border-dark);
        border-radius: 8px;
        padding: 1.3rem 1.6rem;
        box-shadow: var(--shadow-poster);
        position: relative;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        margin-bottom: 1.2rem;
    }

    .bento-card:hover {
        transform: translateY(-2px);
        box-shadow: 6px 6px 0px var(--border-dark), 0 0 16px rgba(245, 212, 0, 0.15);
    }

    .bento-card-gold {
        border-top: 5px solid var(--accent-gold);
    }

    .bento-card-pink {
        border-top: 5px solid var(--accent-pink);
    }

    /* Muted Card Variant for Pending/Unpublished/Empty States */
    .bento-card-muted {
        background: #062217 !important;
        border: 2px dashed rgba(36, 115, 82, 0.6) !important;
        box-shadow: 3px 3px 0px #020C08 !important;
        opacity: 0.88;
    }

    .bento-card-muted:hover {
        transform: none !important;
        box-shadow: 3px 3px 0px #020C08 !important;
    }

    /* Alert / Error Card Variant */
    .bento-card-alert {
        background: linear-gradient(135deg, #240813 0%, #15050C 100%) !important;
        border: 2px solid var(--border-dark) !important;
        border-top: 5px solid var(--accent-alert) !important;
        box-shadow: var(--shadow-poster) !important;
    }

    .bento-label {
        font-family: 'Space Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-size: 0.72rem; /* Minimum 11px floor */
        font-weight: 700;
        color: var(--accent-pink);
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .bento-heading {
        font-family: 'DM Serif Display', serif;
        font-size: 1.6rem;
        color: var(--accent-gold);
        margin: 0 0 0.8rem 0;
        line-height: 1.2;
        text-shadow: 1px 1px 0px var(--border-dark);
    }

    /* Directional Signpost Stat Callouts */
    .signpost-container {
        display: flex;
        gap: 12px;
        margin: 10px 0;
        flex-wrap: wrap;
    }

    .signpost-box {
        border: 2px solid var(--border-dark);
        border-radius: 5px;
        padding: 8px 14px;
        box-shadow: 3px 3px 0px var(--border-dark);
        flex: 1;
        min-width: 130px;
    }

    .signpost-gold {
        background: var(--accent-gold);
        color: var(--text-dark);
    }

    .signpost-pink {
        background: var(--accent-pink);
        color: #FFFFFF;
    }

    /* Only Hero Number gets oversized + kinetic treatment */
    .hero-number {
        font-family: 'DM Serif Display', serif;
        font-size: 2.6rem;
        font-weight: 700;
        line-height: 1;
        margin: 0;
        transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
        display: inline-block;
    }

    .hero-number:hover {
        transform: scale(1.08);
    }

    /* Subordinate static numbers */
    .static-num {
        font-family: 'DM Serif Display', serif;
        font-size: 1.6rem;
        font-weight: 700;
        line-height: 1;
        margin: 0;
        color: var(--accent-gold);
    }

    .static-num-pink {
        color: #FFFFFF;
    }

    .signpost-lbl {
        font-family: 'Space Mono', monospace;
        font-size: 0.7rem; /* Minimum 11px floor */
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 4px;
        opacity: 0.95;
    }

    /* Test Mode Chip for Tamper Toggle */
    .test-mode-chip {
        display: inline-block;
        background: #242416;
        color: var(--accent-gold);
        border: 1.5px solid var(--accent-gold);
        border-radius: 3px;
        font-family: 'Space Mono', monospace;
        font-size: 0.7rem; /* Minimum 11px floor */
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        padding: 2px 8px;
        margin-bottom: 6px;
    }

    .tag-social {
        background: var(--accent-pink);
        color: #FFFFFF !important;
        padding: 5px 12px;
        border-radius: 3px;
        border: 2px solid var(--border-dark);
        font-family: 'Space Mono', monospace;
        font-weight: 700;
        font-size: 0.74rem; /* Minimum 11px floor */
        text-transform: uppercase;
        letter-spacing: 1.2px;
        display: inline-block;
        box-shadow: 2px 2px 0px var(--border-dark);
        transition: transform 0.15s ease;
    }

    .tag-social:hover {
        transform: scale(1.04);
    }

    .tag-web {
        background: var(--accent-gold);
        color: var(--text-dark) !important;
        padding: 5px 12px;
        border-radius: 3px;
        border: 2px solid var(--border-dark);
        font-family: 'Space Mono', monospace;
        font-weight: 700;
        font-size: 0.74rem; /* Minimum 11px floor */
        text-transform: uppercase;
        letter-spacing: 1.2px;
        display: inline-block;
        box-shadow: 2px 2px 0px var(--border-dark);
        transition: transform 0.15s ease;
    }

    .tag-web:hover {
        transform: scale(1.04);
    }

    .hash-code {
        background: #020D08;
        color: var(--accent-gold);
        font-family: 'Space Mono', monospace;
        padding: 12px 14px;
        border-radius: 4px;
        border: 2px solid var(--border-dark);
        border-left: 5px solid var(--accent-gold);
        font-size: 0.8rem;
        line-height: 1.45;
        word-break: break-all;
        overflow-wrap: break-word;
        white-space: pre-wrap;
        box-sizing: border-box;
        margin: 8px 0 14px 0;
        box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.6), 3px 3px 0px var(--border-dark);
    }

    .alert-ok {
        background: linear-gradient(135deg, #073522 0%, #042216 100%);
        color: var(--accent-gold);
        border: 2px solid var(--border-dark);
        border-left: 6px solid var(--accent-gold);
        border-radius: 6px;
        padding: 15px 18px;
        font-family: 'Space Mono', monospace;
        font-weight: 700;
        font-size: 0.84rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: var(--shadow-poster), 0 0 16px var(--accent-gold-dim);
        margin-bottom: 14px;
    }

    .alert-tamper {
        background: linear-gradient(135deg, #320A1C 0%, #1E0510 100%);
        color: #FFA5C8;
        border: 2px solid var(--border-dark);
        border-left: 6px solid var(--accent-alert);
        border-radius: 6px;
        padding: 15px 18px;
        font-family: 'Space Mono', monospace;
        font-weight: 700;
        font-size: 0.84rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: var(--shadow-poster), 0 0 16px var(--accent-alert-dim);
        margin-bottom: 14px;
    }

    .status-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 4px;
        border: 1.5px solid var(--border-dark);
        font-family: 'Space Mono', monospace;
        font-size: 0.72rem; /* Minimum 11px floor */
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 6px;
        box-shadow: 2px 2px 0px var(--border-dark);
    }

    .status-ok {
        background: var(--accent-gold);
        color: var(--text-dark) !important;
    }

    .status-missing {
        background: var(--accent-alert);
        color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('''
<div class="header-bar">
    <span class="header-tag">Decentralized Provenance</span>
    <div class="app-title">VeriTrace</div>
    <div class="app-subtitle">Facial Feature Matching &amp; Cryptographic Blockchain Anchoring</div>
</div>
''', unsafe_allow_html=True)

# Settings in sidebar
st.sidebar.subheader("Configuration")

env_serpapi = os.getenv("SERPAPI_KEY", "")
env_amoy_rpc = os.getenv("AMOY_RPC_URL", "https://polygon-amoy.drpc.org")
env_pk = os.getenv("PRIVATE_KEY", "")
env_contract = os.getenv("CONTRACT_ADDRESS", "")

serpapi_status = "configured" if (env_serpapi and "your_serpapi" not in env_serpapi) else "missing"
chain_status = "configured" if (env_pk and "your_testnet" not in env_pk) else "missing"
contract_status = "configured" if (env_contract and not env_contract.startswith("0x0000")) else "missing"

def _badge(label, status):
    cls = "status-ok" if status == "configured" else "status-missing"
    icon = "●" if status == "configured" else "○"
    return f'<span class="status-badge {cls}">{icon} {label}: {status}</span>'

st.sidebar.markdown(
    _badge("SerpApi", serpapi_status) + "<br>" +
    _badge("Wallet", chain_status) + "<br>" +
    _badge("Contract", contract_status),
    unsafe_allow_html=True,
)

active_serpapi = env_serpapi
active_contract = env_contract
active_pk = env_pk
active_rpc = env_amoy_rpc

st.sidebar.subheader("Model options")
detector_backend = st.sidebar.selectbox("Detector", ["retinaface", "mtcnn", "opencv"], index=0)
embedding_model = st.sidebar.selectbox("Embedding Model", ["Facenet512", "ArcFace", "Facenet"], index=0)
search_target = st.sidebar.radio("Search input", ["Cropped Face", "Original Image"], index=0)
use_crop = (search_target == "Cropped Face")

st.sidebar.markdown("---")
if st.sidebar.button("Clear Active Pipeline", use_container_width=True):
    for k in ["pipeline_result", "verify_result", "tested_is_tampered"]:
        st.session_state.pop(k, None)
    st.rerun()

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('''<div class="bento-card bento-card-gold">
        <div class="bento-label">● Step 01 / Intake</div>
        <div class="bento-heading">Input Image</div>
    </div>''', unsafe_allow_html=True)
    sample_dir = Path("samples")
    sample_files = [f.name for f in sample_dir.glob("*.*") if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]]
    
    input_mode = st.radio("Source", ["Upload file", "Sample library"], index=0)
    selected_image_path = None

    if input_mode == "Sample library":
        if sample_files:
            chosen_sample = st.selectbox("Choose sample", sample_files)
            selected_image_path = str(sample_dir / chosen_sample)
        else:
            st.info("No samples found in samples/ directory. Please upload an image.")
    else:
        uploaded_file = st.file_uploader("Choose an image (JPG, PNG)", type=["jpg", "jpeg", "png", "webp"])
        if uploaded_file is not None:
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            selected_image_path = temp_path

    run_btn = st.button("Run Verification Pipeline", type="primary", disabled=(selected_image_path is None), use_container_width=True)

with col_right:
    st.markdown('''<div class="bento-card bento-card-pink">
        <div class="bento-label">● Step 01 / Target Preview</div>
        <div class="bento-heading">Source Asset</div>
    </div>''', unsafe_allow_html=True)
    if selected_image_path:
        st.image(selected_image_path, caption="Active Target Image", use_container_width=True)
    else:
        st.markdown('''
        <div class="bento-card-muted" style="padding: 2.2rem 1.6rem; text-align: center; border-radius: 6px;">
            <div style="font-family: 'Space Mono', monospace; font-size: 0.78rem; color: var(--text-muted); letter-spacing: 1px; line-height: 1.6;">
                AWAITING ASSET SELECTION<br/>
                <span style="font-size: 0.7rem; color: #58806E;">Pick a sample from the library or upload a face image to preview</span>
            </div>
        </div>
        ''', unsafe_allow_html=True)

if run_btn and selected_image_path:
    with st.spinner("Processing face detection and search..."):
        try:
            # Lazy import heavy modules only when pipeline is triggered
            from src.face import detect_and_embed_face
            from src.search import search_reverse_image
            from src.pipeline import compute_canonical_record_hash
            from src.chain import store_record_on_chain

            with st.status("Detecting face & extracting embedding...", expanded=True) as s1:
                face_data = detect_and_embed_face(
                    image_path=selected_image_path,
                    detector_backend=detector_backend,
                    model_name=embedding_model,
                )
                s1.update(label="Face detected", state="complete", expanded=False)

            with st.status("Querying reverse image search...", expanded=True) as s2:
                search_image = face_data["face_crop_path"] if use_crop else selected_image_path
                search_data = search_reverse_image(
                    search_image,
                    api_key=active_serpapi,
                )
                s2.update(label="Search completed", state="complete", expanded=False)

            with st.status("Creating canonical record...", expanded=True) as s3:
                import hashlib
                with open(selected_image_path, "rb") as f:
                    src_hash = hashlib.sha256(f.read()).hexdigest()

                import uuid, datetime
                rec_id = str(uuid.uuid4())
                timestamp_now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                top_match = search_data["top_match"]
                canonical_payload = {
                    "record_id": rec_id,
                    "source_image_sha256": src_hash,
                    "matched_url": top_match["url"],
                    "matched_domain": top_match["domain"],
                    "match_type": top_match["match_type"],
                    "match_confidence": top_match["confidence"],
                    "result_title": top_match["title"],
                    "timestamp_utc": timestamp_now,
                }
                canonical_json_str, record_hash = compute_canonical_record_hash(canonical_payload)

                full_saved = {
                    **canonical_payload,
                    "record_hash_sha256": record_hash,
                    "face_metadata": {
                        "detector": face_data["detector_backend"],
                        "model": face_data["model_name"],
                        "facial_area": face_data["facial_area"],
                        "embedding_dimensions": face_data["embedding_dimensions"],
                    },
                    "search_metadata": {
                        "public_image_url": search_data["public_image_url"],
                        "top_source": top_match["source"],
                    },
                }

                rec_file = os.path.join("records", f"{rec_id}.json")
                with open(rec_file, "w", encoding="utf-8") as f:
                    json.dump(full_saved, f, indent=2)

                s3.update(label="Record saved", state="complete", expanded=False)

            tx_data = None
            tx_error = None
            if active_pk and "your_testnet" not in active_pk and active_contract and not active_contract.startswith("0x0000"):
                with st.status("Writing record hash to Polygon Amoy...", expanded=True) as s4:
                    try:
                        tx_data = store_record_on_chain(
                            record_hash_sha256=record_hash,
                            private_key=active_pk,
                            contract_address=active_contract,
                            rpc_url=active_rpc,
                        )
                        s4.update(label="Transaction confirmed on-chain", state="complete", expanded=False)
                    except Exception as e:
                        tx_error = str(e)
                        s4.update(label=f"Blockchain write error: {e}", state="error", expanded=True)
                        st.error(f"Blockchain error: {e}")

            st.session_state["pipeline_result"] = {
                "face_data": face_data,
                "search_data": search_data,
                "canonical_payload": canonical_payload,
                "record_hash": record_hash,
                "full_saved": full_saved,
                "record_file": rec_file,
                "tx_data": tx_data,
                "tx_error": tx_error,
            }

        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.exception(e)

if "pipeline_result" in st.session_state:
    res = st.session_state["pipeline_result"]
    face = res["face_data"]
    search = res["search_data"]
    top = search.get("top_match", {})
    tx = res.get("tx_data")
    tx_error = res.get("tx_error")

    # Screen-Printed Repeating Pattern Divider (Rows 1-2)
    st.markdown('<div class="retro-pattern-divider"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # BENTO ROW 1: MATCH HERO & FACE ANALYSIS PROFILE (7 : 5)
    # ══════════════════════════════════════════════════════════
    bento_col1, bento_col2 = st.columns([7, 5], gap="large")

    with bento_col1:
        # Check for empty/no-match state
        has_valid_match = (
            top and
            top.get("domain") and 
            top.get("domain") != "None" and 
            top.get("url") and 
            top.get("confidence", 0) > 0
        )

        if not has_valid_match:
            st.markdown('''
            <div class="bento-card bento-card-muted">
                <div class="bento-label" style="color: var(--text-muted);">● Step 03 / Top Intelligence</div>
                <div class="bento-heading" style="color: #88B8A0;">No Reverse Search Match Located</div>
                <p style="color: #88B8A0; font-family: 'Space Mono', monospace; font-size: 0.76rem; margin: 10px 0 0 0; line-height: 1.5;">
                    No indexed public web documents, social media entities, or news archives corresponded to the provided biometric embedding vector.
                </p>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown('''
            <div class="bento-card bento-card-gold">
                <div class="bento-label">● Step 03 / Top Intelligence</div>
                <div class="bento-heading">Reverse Search Match</div>
            </div>
            ''', unsafe_allow_html=True)

            tag_class = "tag-social" if top.get("is_social") else "tag-web"
            tag_label = "Social Profile" if top.get("is_social") else "Public Web Document"
            conf_pct = int(top["confidence"] * 100)

            # Single Hero Number Callout: Only Match Confidence gets oversized + kinetic treatment
            # Candidate count gets subordinate static treatment
            st.markdown(f'''
            <div class="signpost-container">
                <div class="signpost-box signpost-gold">
                    <div class="hero-number">{conf_pct}%</div>
                    <div class="signpost-lbl">Confidence Match</div>
                </div>
                <div class="signpost-box signpost-pink">
                    <div class="static-num static-num-pink">#{search.get("total_results", 0)}</div>
                    <div class="signpost-lbl">Candidate Indices</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

            st.markdown(f'<span class="{tag_class}">{tag_label}</span>', unsafe_allow_html=True)
            
            # Secondary row for domain & source engine
            st.markdown(
                f'<div style="font-family: \'Space Mono\', monospace; font-size: 0.78rem; margin: 8px 0 4px 0; color: var(--text-muted);">'
                f'<strong style="color: var(--text-light);">Domain:</strong> <code style="color: var(--accent-gold);">{top["domain"]}</code> &nbsp;|&nbsp; '
                f'<strong style="color: var(--text-light);">Engine:</strong> {top["source"]}'
                f'</div>',
                unsafe_allow_html=True
            )

            st.markdown(f"**Snippet:** {top['title']}")
            if top["url"] and top["url"].startswith("http"):
                st.markdown(f"[{top['url']}]({top['url']})")

            st.progress(top["confidence"], text=f"Rank Match Confidence: {conf_pct}%")

            if top.get("thumbnail"):
                st.image(top["thumbnail"], caption="Target Match Preview", width=120)

            # Candidates expander
            if search.get("candidates"):
                with st.expander(f"Inspect All Matches ({search['total_results']} records found)"):
                    for cand in search.get("candidates", []):
                        st.markdown(f"- **#{cand['rank']}** [{cand['domain']}]({cand['url']}) — {cand['title']} (`{cand['confidence']}`)")

    with bento_col2:
        st.markdown('''
        <div class="bento-card bento-card-pink">
            <div class="bento-label">● Step 02 / Biometric Vector</div>
            <div class="bento-heading">Face Analysis</div>
        </div>
        ''', unsafe_allow_html=True)

        f_col_img, f_col_stats = st.columns([5, 6])
        with f_col_img:
            st.image(face["face_crop_path"], caption=f"Crop ({face['detector_backend']})", use_container_width=True)
        with f_col_stats:
            # Subordinate static numbers (no kinetic zoom)
            st.markdown(f'''
            <div class="signpost-box signpost-gold" style="margin-bottom: 8px;">
                <div class="static-num">{face['embedding_dimensions']}</div>
                <div class="signpost-lbl">Vector Floats</div>
            </div>
            <div class="signpost-box signpost-pink">
                <div class="static-num static-num-pink">{face['confidence'] * 100:.0f}%</div>
                <div class="signpost-lbl">Detect Confidence</div>
            </div>
            ''', unsafe_allow_html=True)
            st.caption(f"Detector: `{face['detector_backend']}` | Model: `{face['model_name']}`")

    # Screen-Printed Repeating Pattern Divider between Rows 1 & 2
    st.markdown('<div class="retro-pattern-divider"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # BENTO ROW 2: CANONICAL RECORD & ON-CHAIN PROVENANCE (6 : 6)
    # ══════════════════════════════════════════════════════════
    bento_rec, bento_chain = st.columns([6, 6], gap="large")

    with bento_rec:
        # Solid opaque canonical record (Card C)
        st.markdown('''
        <div class="bento-card bento-card-gold">
            <div class="bento-label">● Step 04 / Immutable Proof</div>
            <div class="bento-heading">Canonical Record</div>
        </div>
        ''', unsafe_allow_html=True)
        st.markdown(f"**Record ID:** `{res['canonical_payload']['record_id']}`")
        st.markdown("**SHA-256 Cryptographic Hash:**")
        st.markdown(f'<div class="hash-code">0x{res["record_hash"]}</div>', unsafe_allow_html=True)
        st.json(res["canonical_payload"])

        st.download_button(
            label="Download Signed JSON Ticket",
            data=json.dumps(res["full_saved"], indent=2),
            file_name=f"record_{res['canonical_payload']['record_id']}.json",
            mime="application/json",
        )

    with bento_chain:
        # Card D: Solid if confirmed, Muted if pending, Alert if write failure
        if tx:
            st.markdown('''
            <div class="bento-card bento-card-pink">
                <div class="bento-label">● Step 05 / Smart Contract Provenance</div>
                <div class="bento-heading">Polygon Amoy Registry</div>
            </div>
            ''', unsafe_allow_html=True)
            st.markdown(f'''
            <div class="alert-ok">
                <strong>CONFIRMED ON-CHAIN</strong> — Anchored at Block #{tx['block_number']}
            </div>
            ''', unsafe_allow_html=True)
            st.markdown(f"**On-Chain Registry ID:** `#{tx['record_id']}`")
            st.markdown(f"**Block Number:** `#{tx['block_number']}` | **Gas Units:** `{tx['gas_used']}`")
            st.markdown(f"**Submitter Address:** `{tx['submitter']}`")
            st.markdown(f"**Explorer Verification:** [{tx['polygonscan_url']}]({tx['polygonscan_url']})")
        elif tx_error:
            st.markdown(f'''
            <div class="bento-card bento-card-alert">
                <div class="bento-label" style="color: var(--accent-alert);">● Step 05 / Blockchain Write Failure</div>
                <div class="bento-heading" style="color: #FFA5C8;">Transaction Failed</div>
                <p style="color: #FFA5C8; font-family: 'Space Mono', monospace; font-size: 0.76rem; margin-bottom: 12px; word-break: break-all;">
                    ERROR: {tx_error}
                </p>
            </div>
            ''', unsafe_allow_html=True)
            if st.button("Retry On-Chain Anchoring"):
                with st.spinner("Retrying contract submission..."):
                    try:
                        from src.chain import store_record_on_chain
                        tx_retry = store_record_on_chain(
                            record_hash_sha256=res["record_hash"],
                            private_key=active_pk,
                            contract_address=active_contract,
                            rpc_url=active_rpc,
                        )
                        res["tx_data"] = tx_retry
                        res["tx_error"] = None
                        st.session_state["pipeline_result"] = res
                        st.rerun()
                    except Exception as e:
                        st.error(f"Retry failed: {e}")
        else:
            # Muted variant for record-not-yet-published
            st.markdown('''
            <div class="bento-card bento-card-muted">
                <div class="bento-label" style="color: var(--text-muted);">● Step 05 / Smart Contract Pending</div>
                <div class="bento-heading" style="color: #88B8A0;">Record Not Yet Published</div>
                <div style="font-family: 'Space Mono', monospace; font-size: 0.76rem; color: #88B8A0; margin-bottom: 12px; line-height: 1.4;">
                    STATUS: CANONICAL DIGEST PREPARED • AWAITING ON-CHAIN ANCHORING
                </div>
            </div>
            ''', unsafe_allow_html=True)
            if st.button("Publish Record to Polygon Amoy"):
                with st.spinner("Submitting contract transaction..."):
                    try:
                        from src.chain import store_record_on_chain
                        tx_new = store_record_on_chain(
                            record_hash_sha256=res["record_hash"],
                            private_key=active_pk,
                            contract_address=active_contract,
                            rpc_url=active_rpc,
                        )
                        res["tx_data"] = tx_new
                        res["tx_error"] = None
                        st.session_state["pipeline_result"] = res
                        st.rerun()
                    except Exception as e:
                        res["tx_error"] = str(e)
                        st.session_state["pipeline_result"] = res
                        st.error(f"Blockchain submission failed: {e}")

    # Serious Thin Gold Divider before Verification Gate
    st.markdown('<div class="serious-gold-divider"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # BENTO ROW 3: SPLIT VERIFICATION SUITE (Card E1 + Card E2)
    # ══════════════════════════════════════════════════════════
    col_e1, col_e2 = st.columns([1, 1], gap="large")

    with col_e2:
        # CARD E2: Action / Result Area + Tamper Simulation Test Mode
        st.markdown('''
        <div class="bento-card bento-card-pink">
            <div class="bento-label">● Step 06 / Trust Engine</div>
            <div class="bento-heading">Audit &amp; Integrity Controls</div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown('<span class="test-mode-chip">TEST MODE CONTROL</span>', unsafe_allow_html=True)
        simulate_tamper = st.checkbox(
            "Simulate tampered payload (alters title & metadata to test mismatch detection)",
            value=False,
            key="simulate_tamper_toggle"
        )

        reverify_btn = st.button("Audit Record Integrity", type="primary", use_container_width=True)

        if reverify_btn:
            if not tx and not active_contract:
                st.error("Missing smart contract address or anchored record ID.")
            else:
                record_id_to_check = tx["record_id"] if tx else 1
                payload_to_test = dict(res["canonical_payload"])

                if simulate_tamper:
                    payload_to_test["result_title"] = "TAMPERED / UNVERIFIED DATA INJECTION"
                    payload_to_test["match_confidence"] = 0.999

                with st.spinner("Querying Ethereum JSON-RPC..."):
                    try:
                        from src.chain import verify_record
                        verify_res = verify_record(
                            record_id=record_id_to_check,
                            local_record_or_file=payload_to_test,
                            contract_address=active_contract,
                            rpc_url=active_rpc,
                        )
                        st.session_state["verify_result"] = verify_res
                        st.session_state["tested_is_tampered"] = simulate_tamper
                    except Exception as e:
                        st.error(f"Contract verification call failed: {e}")

        # Render result banner in Card E2 if verification has been performed
        v_res = st.session_state.get("verify_result")
        if v_res:
            if v_res["is_valid"]:
                st.markdown('''
                <div class="alert-ok">
                    <strong>AUTHENTIC RECORD CONFIRMED</strong><br/>
                    Local hash perfectly matches Polygon Amoy on-chain registry state.
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown('''
                <div class="alert-tamper">
                    <strong>MISMATCH DETECTED / TAMPER ALERT</strong><br/>
                    Local digest differs from the immutable smart contract record!
                </div>
                ''', unsafe_allow_html=True)

    with col_e1:
        # CARD E1: Hash Comparison Only (Local Hash vs On-Chain Hash, side by side or stacked)
        st.markdown('''
        <div class="bento-card bento-card-gold">
            <div class="bento-label">● Step 06 / Cryptographic Digest Comparison</div>
            <div class="bento-heading">Hash Comparison</div>
        </div>
        ''', unsafe_allow_html=True)

        v_res = st.session_state.get("verify_result")
        if v_res:
            local_hash_disp = v_res["local_hash"]
            onchain_hash_disp = v_res["onchain_hash"]
        else:
            local_hash_disp = f"0x{res['record_hash']}"
            if tx:
                onchain_hash_disp = f"0x{res['record_hash']}"
            else:
                onchain_hash_disp = "0x0000000000000000000000000000000000000000000000000000000000000000 (Pending Publication)"

        st.markdown("**Local Record Digest:**")
        st.markdown(f'<div class="hash-code">{local_hash_disp}</div>', unsafe_allow_html=True)

        st.markdown("**Immutable On-Chain Digest:**")
        st.markdown(f'<div class="hash-code">{onchain_hash_disp}</div>', unsafe_allow_html=True)

        if v_res:
            match_status = "MATCH CONFIRMED" if v_res["is_valid"] else "MISMATCH / CORRUPTED"
            status_cls = "status-ok" if v_res["is_valid"] else "status-missing"
            st.markdown(f'<span class="status-badge {status_cls}">DIGEST AUDIT: {match_status}</span>', unsafe_allow_html=True)
        else:
            st.caption("Click 'Audit Record Integrity' to query live state from Polygon Amoy.")

