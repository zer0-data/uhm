import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import streamlit as st


def _load_api_url() -> str:
    env_url = os.environ.get("SHEET_API_URL", "").strip()
    if env_url:
        return env_url

    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            url = str(cfg.get("SHEET_API_URL", "")).strip()
            if url:
                return url
        except Exception:
            pass
    return ""


def _load_images_cfg() -> Dict[str, Optional[str]]:
    """Load optional image paths/URLs from env or config.json.

    Keys: HEADER_IMAGE, SIDEBAR_IMAGE, FOOTER_IMAGE
    Values can be local file paths or URLs. Missing entries become None.
    """
    keys = ["HEADER_IMAGE", "SIDEBAR_IMAGE", "FOOTER_IMAGE"]
    result: Dict[str, Optional[str]] = {k: None for k in keys}

    # Env first
    for k in keys:
        v = os.environ.get(k)
        if v:
            result[k] = v

    # Config fallback
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for k in keys:
                if not result[k]:
                    val = cfg.get(k)
                    if isinstance(val, str) and val.strip():
                        result[k] = val.strip()
        except Exception:
            pass

    # Normalize relative paths from env/config to absolute if files exist
    def _is_url(s: str) -> bool:
        return s.startswith("http://") or s.startswith("https://")

    for k, v in list(result.items()):
        if not v or _is_url(v) or os.path.isabs(v):
            continue
        candidate = os.path.join(base_dir, v)
        if os.path.isfile(candidate):
            result[k] = candidate

    # Default files from ./images if still not provided
    images_dir = os.path.join(base_dir, "images")
    if os.path.isdir(images_dir):
        candidates = {
            "HEADER_IMAGE": ["header.png", "header.jpg", "header.jpeg", "header.webp"],
            "SIDEBAR_IMAGE": ["sidebar.png", "sidebar.jpg", "sidebar.jpeg", "sidebar.webp"],
            "FOOTER_IMAGE": ["footer.png", "footer.jpg", "footer.jpeg", "footer.webp"],
        }
        for key, names in candidates.items():
            if result.get(key):
                continue
            for name in names:
                p = os.path.join(images_dir, name)
                if os.path.isfile(p):
                    result[key] = p
                    break
    return result


# --- API functions (kept same interface as tkinter app logic) ---
def fetch_grievances(api_url: str) -> List[Dict[str, Any]]:
    resp = requests.get(api_url, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        return []
    return data


def submit_grievance(api_url: str, text: str) -> None:
    payload = {
        "Timestamp": datetime.now().isoformat(timespec="seconds"),
        "Grievance": text,
        "Status": "",
    }
    resp = requests.post(api_url, json=payload, timeout=20)
    resp.raise_for_status()


def _sort_rows_desc(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def parse_ts(row):
        ts = str(row.get("Timestamp") or row.get("timestamp") or "")
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.min

    return sorted(rows, key=parse_ts, reverse=True)


def main():
    st.set_page_config(page_title="Jeremiahpaglu", layout="centered")

    # Inject custom CSS for light pink background and gentle accents
    st.markdown(
        """
        <style>
        /* Page background */
        .stApp {
            background-color: #FFEFF4; /* light pink */
        }
        /* Make ALL text black by default */
        html, body, .stApp, .stMarkdown, .stText, .stWrite, .st-emotion-cache, .stExpander, 
        h1, h2, h3, h4, h5, h6, p, label, span, div, code, pre, li, summary,
        section[data-testid="stSidebar"], section[data-testid="stSidebar"] * {
            color: #000000 !important;
        }
        /* Links also black */
        a, a:visited, a:hover, a:active { color: #000000 !important; }
        /* Text area text & placeholder black; bg white */
        .stTextArea textarea {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            caret-color: #000000 !important;
        }
        .stTextArea textarea::placeholder { color: #000000 !important; }
        /* Cards/expanders neutral background */
        .stExpander, .stMarkdown { background-color: #FFFFFF !important; }
        /* Primary button color with black text (purple) */
        .stButton>button,
        button[kind="primary"],
        div[data-testid="stFormSubmitButton"] button,
        div[data-testid="baseButton-primary"] {
            background-color: #7C3AED !important; /* purple */
            background-image: none !important;
            border: 1px solid #7C3AED !important;
            color: #000000 !important; /* keep text black as requested */
            box-shadow: none !important;
        }
        .stButton>button:hover,
        button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] button:hover,
        div[data-testid="baseButton-primary"]:hover,
        .stButton>button:focus,
        button[kind="primary"]:focus,
        div[data-testid="stFormSubmitButton"] button:focus,
        div[data-testid="baseButton-primary"]:focus,
        .stButton>button:active,
        button[kind="primary"]:active,
        div[data-testid="stFormSubmitButton"] button:active,
        div[data-testid="baseButton-primary"]:active {
            background-color: #6D28D9 !important;
            border-color: #6D28D9 !important;
            color: #000000 !important;
            box-shadow: none !important;
        }

        /* Sidebar image: auto-fill width */
        section[data-testid="stSidebar"] img {
            width: 100% !important;
            max-width: 100% !important;
            height: auto !important;
            display: block !important;
            object-fit: contain !important; /* change to cover if you prefer crop */
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Why Bhakti hates me 😭😭")

    api_url = _load_api_url()
    if not api_url:
        st.error("Missing API URL. Set SHEET_API_URL or provide config.json with SHEET_API_URL.")
        st.stop()

    # Optional images (header/sidebar/footer)
    images_cfg = _load_images_cfg()
    if images_cfg.get("HEADER_IMAGE"):
        st.image(images_cfg["HEADER_IMAGE"], use_container_width=True)

    # Sidebar image (optional) - always render if present
    if images_cfg.get("SIDEBAR_IMAGE"):
        with st.sidebar:
            st.image(images_cfg["SIDEBAR_IMAGE"], use_container_width=True)

    # Submission form
    with st.form("submit_form", clear_on_submit=True):
        thought = st.text_area("why is me worst?🥺", height=140, placeholder="Pasand bhi hoon mai tujhe😭")
        submitted = st.form_submit_button("Submit Thought")
        if submitted:
            if not thought.strip():
                st.warning("Please write something before submitting.")
            else:
                try:
                    submit_grievance(api_url, thought.strip())
                except Exception as e:
                    st.error(f"Couldn't submit your thought.\n\n{e}")
                    st.stop()
                st.success("Your thought has been logged.")
                # Trigger a rerun to refresh history immediately
                st.rerun()

    # History
    st.markdown("---")
    st.subheader("Do you even love me?🥺")
    refresh = st.button("Refresh 🔄")
    if refresh:
        st.rerun()

    try:
        rows = fetch_grievances(api_url)
    except Exception as e:
        st.error(f"Couldn't retrieve history.\n\n{e}")
        st.stop()

    rows = _sort_rows_desc(rows)

    if not rows:
        st.info("Nothing to complain about huh, I love u ❤️")
    else:
        for row in rows:
            ts = str(row.get("Timestamp") or "").strip()
            status = str(row.get("Status") or "").strip()
            grievance = str(row.get("Grievance") or "").strip()

            title_bits = []
            if ts:
                title_bits.append(ts)
            if status:
                title_bits.append(f"Status: {status}")
            title = " • ".join(title_bits) if title_bits else "Submission"

            with st.expander(title, expanded=False):
                st.write(grievance if grievance else "(No text)")

    # Footer image (optional)
    if images_cfg.get("FOOTER_IMAGE"):
        st.markdown("\n---\n")
        st.image(images_cfg["FOOTER_IMAGE"], use_container_width=True)


if __name__ == "__main__":
    main()
