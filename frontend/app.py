import os
import textwrap

import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Uptime Monitor", page_icon="📡", layout="wide")

st_autorefresh(interval=15_000, key="auto_refresh")


def html(s: str):
    """Render HTML safely. Dedent first so Streamlit's markdown parser
    doesn't mistake indented lines for a code block."""
    st.markdown(textwrap.dedent(s), unsafe_allow_html=True)


# ---------- Styling: dark theme ----------
html("""
<style>
.stApp {
    background-color: #0e1117;
}
.pulse-header h1 {
    font-size: 2rem;
    font-weight: 700;
    margin: 0;
    background: linear-gradient(90deg, #34d399, #22d3ee);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.pulse-sub {
    color: #8b949e;
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
}
.metric-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.metric-card {
    flex: 1;
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 1rem 1.25rem;
}
.metric-card .label {
    color: #8b949e;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.metric-card .value {
    font-size: 1.8rem;
    font-weight: 700;
    margin-top: 0.2rem;
}
.value-up { color: #34d399; }
.value-down { color: #f87171; }
.value-total { color: #e6edf3; }

.status-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-left: 4px solid #30363d;
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    margin-bottom: 0.6rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.status-card.up { border-left-color: #34d399; }
.status-card.down { border-left-color: #f87171; }
.status-card.pending { border-left-color: #d29922; }

.status-left .name {
    font-weight: 600;
    color: #e6edf3;
    font-size: 1rem;
}
.status-left .url {
    color: #8b949e;
    font-size: 0.82rem;
}
.status-right {
    text-align: right;
}
.badge {
    display: inline-block;
    padding: 0.15rem 0.65rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
}
.badge-up { background: rgba(52,211,153,0.15); color: #34d399; }
.badge-down { background: rgba(248,113,113,0.15); color: #f87171; }
.badge-pending { background: rgba(210,153,34,0.15); color: #d29922; }

.status-meta {
    color: #8b949e;
    font-size: 0.78rem;
    margin-top: 0.2rem;
}
</style>
""")

html("""
<div class="pulse-header">
    <h1>📡 Uptime Monitor</h1>
</div>
<div class="pulse-sub">Checks every registered URL every 60 seconds.</div>
""")

# ---------- Fetch data ----------
try:
    resp = requests.get(f"{BACKEND_URL}/api/urls", timeout=10)
    resp.raise_for_status()
    urls = resp.json()
    backend_reachable = True
except requests.exceptions.RequestException as e:
    st.error(f"Could not reach backend at {BACKEND_URL}: {e}")
    urls = []
    backend_reachable = False

# ---------- Metrics row ----------
total = len(urls)
up_count = sum(1 for u in urls if u.get("latest_check") and u["latest_check"]["is_up"])
down_count = sum(
    1 for u in urls if u.get("latest_check") and not u["latest_check"]["is_up"]
)

if backend_reachable:
    html(f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="label">Monitored</div>
            <div class="value value-total">{total}</div>
        </div>
        <div class="metric-card">
            <div class="label">Up</div>
            <div class="value value-up">{up_count}</div>
        </div>
        <div class="metric-card">
            <div class="label">Down</div>
            <div class="value value-down">{down_count}</div>
        </div>
    </div>
    """)

# ---------- Add URL form ----------
with st.expander("➕ Add a URL to monitor", expanded=(total == 0)):
    with st.form("add_url_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 3, 1])
        name = col1.text_input("Name", placeholder="e.g. Company Homepage")
        url = col2.text_input("URL", placeholder="https://example.com")
        submitted = col3.form_submit_button("Add", use_container_width=True)

        if submitted:
            if not name or not url:
                st.warning("Both a name and a URL are required.")
            else:
                try:
                    r = requests.post(
                        f"{BACKEND_URL}/api/urls",
                        json={"name": name, "url": url},
                        timeout=10,
                    )
                    if r.status_code == 201:
                        st.success(f"Added {url}. First check running now.")
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Failed to add URL."))
                except requests.exceptions.RequestException as e:
                    st.error(f"Could not reach backend: {e}")

# ---------- Status list ----------
if backend_reachable and not urls:
    st.info("No URLs registered yet. Add one above to start monitoring.")
elif backend_reachable:
    for u in urls:
        latest = u.get("latest_check")

        if latest is None:
            state = "pending"
            badge = '<span class="badge badge-pending">PENDING</span>'
            meta = "Waiting on first check"
        elif latest["is_up"]:
            state = "up"
            badge = '<span class="badge badge-up">UP</span>'
            meta = f"HTTP {latest['status_code']} · {latest['response_time_ms']} ms"
        else:
            state = "down"
            badge = '<span class="badge badge-down">DOWN</span>'
            code = latest["status_code"] if latest["status_code"] else "no response"
            rt = latest.get("response_time_ms")
            meta = f"{code} · {rt} ms" if rt is not None else f"{code}"

        checked_at = ""
        if latest and latest.get("checked_at"):
            checked_at = f"Last checked: {latest['checked_at']}"

        html(f"""
        <div class="status-card {state}">
            <div class="status-left">
                <div class="name">{u['name']}</div>
                <div class="url">{u['url']}</div>
            </div>
            <div class="status-right">
                {badge}
                <div class="status-meta">{meta}</div>
                <div class="status-meta">{checked_at}</div>
            </div>
        </div>
        """)

    st.divider()
    with st.expander("🗑️ Remove a monitored URL"):
        id_map = {f'{u["name"]} ({u["url"]})': u["id"] for u in urls}
        choice = st.selectbox("Select a URL to remove", options=list(id_map.keys()))
        if st.button("Remove"):
            target_id = id_map[choice]
            del_resp = requests.delete(f"{BACKEND_URL}/api/urls/{target_id}", timeout=10)
            if del_resp.status_code == 204:
                st.success("Removed.")
                st.rerun()
            else:
                st.error("Failed to remove URL.")
