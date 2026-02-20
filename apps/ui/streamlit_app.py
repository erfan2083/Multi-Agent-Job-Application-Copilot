from __future__ import annotations

import requests
import streamlit as st

API = st.secrets.get("api_url", "http://localhost:8000")

st.title("Multi-Agent Job Application Copilot")

with st.sidebar:
    st.subheader("Login (required for LLM usage)")
    username = st.text_input("Username", value="admin")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        r = requests.post(f"{API}/auth/login", json={"username": username, "password": password}, timeout=30)
        if r.ok:
            st.session_state["token"] = r.json().get("access_token")
            st.success("Logged in")
        else:
            st.error("Login failed")

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
    st.json(resp.json())

st.subheader("LLM prompt test")
prompt = st.text_area("Prompt", value="Summarize candidate strengths.")
if st.button("Call LLM"):
    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.post(f"{API}/llm/generate", json={"prompt": prompt}, headers=headers, timeout=60)
    st.json(r.json())
