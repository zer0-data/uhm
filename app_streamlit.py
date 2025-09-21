import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

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
    st.set_page_config(page_title="A Penny for Your Thoughts", layout="centered")
    st.title("A Penny for Your Thoughts")

    api_url = _load_api_url()
    if not api_url:
        st.error("Missing API URL. Set SHEET_API_URL or provide config.json with SHEET_API_URL.")
        st.stop()

    # Submission form
    with st.form("submit_form", clear_on_submit=True):
        thought = st.text_area("What's on your mind?", height=140, placeholder="Type your thought here…")
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
    st.subheader("Submission History")
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
        st.info("No submissions yet. Be the first to share a thought!")
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


if __name__ == "__main__":
    main()
