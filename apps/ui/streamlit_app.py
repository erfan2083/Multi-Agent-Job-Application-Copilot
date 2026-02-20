from __future__ import annotations

import requests
import streamlit as st

API = st.secrets.get("api_url", "http://localhost:8000")

st.title("Multi-Agent Job Application Copilot")
resume_text = st.text_area("Resume text", height=250)
remote_only = st.checkbox("Remote only", value=True)
include_keywords = st.text_input("Include keywords (comma-separated)")
exclude_keywords = st.text_input("Exclude keywords (comma-separated)")

if st.button("Run pipeline"):
    payload = {
        "resume_text": resume_text,
        "preferences": {
            "remote_only": remote_only,
            "include_keywords": [x.strip() for x in include_keywords.split(",") if x.strip()],
            "exclude_keywords": [x.strip() for x in exclude_keywords.split(",") if x.strip()],
        },
    }
    resp = requests.post(f"{API}/reports/run", json=payload, timeout=120)
    data = resp.json()
    st.json(data)
