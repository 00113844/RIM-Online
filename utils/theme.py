"""
Shared UWA brand theme injector for all Streamlit pages.

UWA Primary Brand Colours
  Navy Blue  : #003087
  Gold       : #DAAA00
  White      : #FFFFFF
  Light grey : #F4F7FB
"""
from __future__ import annotations

import streamlit as st

# ── Colour tokens ──────────────────────────────────────────────────────────────
UWA_NAVY   = "#003087"
UWA_NAVY_D = "#00235e"   # darker navy for hover/press
UWA_NAVY_L = "#ccd6e8"   # light navy tint (borders, dividers)
UWA_GOLD   = "#DAAA00"
UWA_GOLD_L = "#f5e9a0"   # light gold tint
UWA_WHITE  = "#FFFFFF"
UWA_BG     = "#F4F7FB"   # page background
UWA_BG2    = "#E8EDF5"   # card / sidebar background
UWA_TEXT   = "#1A1A2E"
UWA_TEXT_M = "#4A5568"   # muted text
UWA_GREEN  = "#1B8A4E"   # success
UWA_RED    = "#C0392B"   # error/danger

_CSS = """
/* ── Google Font ──────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Root variables ────────────────────────────────────────────────────── */
:root {
  --uwa-navy   : #003087;
  --uwa-navy-d : #00235e;
  --uwa-navy-l : #ccd6e8;
  --uwa-gold   : #DAAA00;
  --uwa-gold-l : #f5e9a0;
  --uwa-bg     : #F4F7FB;
  --uwa-bg2    : #E8EDF5;
  --uwa-text   : #1A1A2E;
  --uwa-text-m : #4A5568;
  --uwa-green  : #1B8A4E;
  --uwa-red    : #C0392B;
  --radius     : 8px;
  --shadow     : 0 2px 10px rgba(0,48,135,0.10);
}

/* ── Base app ───────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  color: var(--uwa-text);
}

.stApp {
  background: var(--uwa-bg) !important;
}

/* ── Sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: var(--uwa-navy) !important;
  border-right: 3px solid var(--uwa-gold) !important;
}
[data-testid="stSidebar"] * {
  color: #ffffff !important;
}
[data-testid="stSidebarNav"] a span {
  color: rgba(255,255,255,0.85) !important;
  font-size: 0.92rem;
  font-weight: 500;
}
[data-testid="stSidebarNav"] a:hover span,
[data-testid="stSidebarNav"] .active span {
  color: var(--uwa-gold) !important;
  font-weight: 700;
}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
  color: #ffffff !important;
}
/* Sidebar collapse button */
[data-testid="collapsedControl"] {
  background: var(--uwa-navy) !important;
  color: #fff !important;
}

/* ── Top header / toolbar ───────────────────────────────────────────────── */
[data-testid="stHeader"] {
  background: var(--uwa-navy) !important;
  border-bottom: 3px solid var(--uwa-gold);
}

/* ── Page titles ────────────────────────────────────────────────────────── */
h1 {
  color: var(--uwa-navy) !important;
  font-weight: 700 !important;
  font-size: 1.85rem !important;
  border-bottom: 3px solid var(--uwa-gold);
  padding-bottom: 0.35rem;
  margin-bottom: 1.2rem !important;
}
h2 {
  color: var(--uwa-navy) !important;
  font-weight: 600 !important;
  font-size: 1.35rem !important;
}
h3 {
  color: var(--uwa-navy) !important;
  font-weight: 600 !important;
  font-size: 1.1rem !important;
}

/* ── Subheader (st.subheader) ───────────────────────────────────────────── */
[data-testid="stMarkdownContainer"] h3 {
  color: var(--uwa-navy) !important;
  border-left: 4px solid var(--uwa-gold);
  padding-left: 0.6rem;
  font-size: 1.05rem !important;
}

/* ── Primary buttons ─────────────────────────────────────────────────────── */
.stButton > button[kind="primary"],
.stButton > button {
  background: var(--uwa-navy) !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: var(--radius) !important;
  font-weight: 600 !important;
  font-size: 0.88rem !important;
  padding: 0.45rem 1.1rem !important;
  transition: background 0.18s, transform 0.12s, box-shadow 0.18s;
  box-shadow: var(--shadow) !important;
}
.stButton > button:hover {
  background: var(--uwa-navy-d) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(0,48,135,0.22) !important;
}
.stButton > button:active {
  transform: translateY(0);
}

/* Download buttons – gold accent */
.stDownloadButton > button {
  background: var(--uwa-gold) !important;
  color: var(--uwa-navy) !important;
  font-weight: 700 !important;
  border: none !important;
  border-radius: var(--radius) !important;
  padding: 0.45rem 1.1rem !important;
}
.stDownloadButton > button:hover {
  background: #c29900 !important;
  transform: translateY(-1px);
}

/* ── Metric cards ───────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: #ffffff;
  border: 1px solid var(--uwa-navy-l);
  border-top: 4px solid var(--uwa-navy);
  border-radius: var(--radius);
  padding: 1rem 1.2rem !important;
  box-shadow: var(--shadow);
}
[data-testid="stMetricLabel"] {
  color: var(--uwa-text-m) !important;
  font-size: 0.82rem !important;
  font-weight: 600 !important;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
[data-testid="stMetricValue"] {
  color: var(--uwa-navy) !important;
  font-size: 1.6rem !important;
  font-weight: 700 !important;
}

/* ── Info / success / warning / error alerts ────────────────────────────── */
.stAlert[data-baseweb="notification"] {
  border-radius: var(--radius) !important;
  font-size: 0.9rem;
}
div[data-testid="stInfo"] {
  background: #EAF0FB !important;
  border-left: 4px solid var(--uwa-navy) !important;
  color: var(--uwa-navy) !important;
  border-radius: var(--radius);
}
div[data-testid="stSuccess"] {
  background: #E8F6EF !important;
  border-left: 4px solid var(--uwa-green) !important;
  border-radius: var(--radius);
}
div[data-testid="stWarning"] {
  background: #FFF9E0 !important;
  border-left: 4px solid var(--uwa-gold) !important;
  border-radius: var(--radius);
}

/* ── Tabs ───────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  border-bottom: 2px solid var(--uwa-navy-l) !important;
  gap: 4px;
}
.stTabs [data-baseweb="tab"] {
  border-radius: var(--radius) var(--radius) 0 0 !important;
  font-weight: 600 !important;
  font-size: 0.88rem !important;
  color: var(--uwa-text-m) !important;
  padding: 0.5rem 1.1rem !important;
  background: transparent !important;
}
.stTabs [data-baseweb="tab"]:hover {
  background: var(--uwa-bg2) !important;
  color: var(--uwa-navy) !important;
}
.stTabs [aria-selected="true"] {
  background: var(--uwa-navy) !important;
  color: #fff !important;
  border-color: transparent !important;
}

/* ── Data tables / dataframes ───────────────────────────────────────────── */
[data-testid="stDataFrame"] table thead tr {
  background: var(--uwa-navy) !important;
  color: #fff !important;
}
[data-testid="stDataFrame"] table thead th {
  color: #fff !important;
  font-weight: 600 !important;
  font-size: 0.83rem !important;
  letter-spacing: 0.03em;
  border: none !important;
}
[data-testid="stDataFrame"] table tbody tr:nth-child(even) {
  background: var(--uwa-bg2) !important;
}
[data-testid="stDataFrame"] table tbody tr:hover {
  background: var(--uwa-gold-l) !important;
}

/* ── Form fields ────────────────────────────────────────────────────────── */
[data-baseweb="input"],
[data-baseweb="select"],
[data-baseweb="textarea"],
[data-baseweb="base-input"] {
  border-color: var(--uwa-navy-l) !important;
  border-radius: var(--radius) !important;
  background: #ffffff !important;
}
[data-baseweb="input"]:focus-within,
[data-baseweb="select"]:focus-within {
  border-color: var(--uwa-navy) !important;
  box-shadow: 0 0 0 2px rgba(0,48,135,0.18) !important;
}

/* ── Expander ───────────────────────────────────────────────────────────── */
details[data-testid="stExpander"] {
  border: 1px solid var(--uwa-navy-l) !important;
  border-radius: var(--radius) !important;
  background: #ffffff;
}
details[data-testid="stExpander"] summary {
  color: var(--uwa-navy) !important;
  font-weight: 600 !important;
}

/* ── Containers with border ─────────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] > div {
  border: 1px solid var(--uwa-navy-l) !important;
  border-radius: var(--radius) !important;
  background: #ffffff;
  box-shadow: var(--shadow);
}

/* ── Plotly charts – rounded wrapper ─────────────────────────────────────── */
[data-testid="stPlotlyChart"] {
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow);
  background: #ffffff;
}

/* ── Page-link cards ─────────────────────────────────────────────────────── */
a[data-testid="stPageLink-NavLink"] {
  border: 1px solid var(--uwa-navy-l) !important;
  border-radius: var(--radius) !important;
  background: #ffffff !important;
  padding: 0.5rem 0.9rem !important;
  font-weight: 600 !important;
  color: var(--uwa-navy) !important;
  transition: background 0.15s, transform 0.12s;
  display: block;
  margin-bottom: 0.5rem;
}
a[data-testid="stPageLink-NavLink"]:hover {
  background: var(--uwa-bg2) !important;
  border-color: var(--uwa-navy) !important;
  transform: translateX(3px);
}

/* ── Custom UWA components ──────────────────────────────────────────────── */
.uwa-page-header {
  background: linear-gradient(135deg, var(--uwa-navy) 0%, #004dc5 100%);
  color: #fff;
  padding: 1.4rem 2rem;
  border-radius: 0 0 var(--radius) var(--radius);
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.2rem;
  box-shadow: 0 4px 18px rgba(0,48,135,0.18);
}
.uwa-page-header .header-title {
  font-size: 1.55rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0;
  line-height: 1.15;
}
.uwa-page-header .header-sub {
  font-size: 0.88rem;
  color: rgba(255,255,255,0.75);
  margin: 0.2rem 0 0 0;
}
.uwa-gold-bar {
  height: 4px;
  background: var(--uwa-gold);
  border-radius: 2px;
  margin: 0.4rem 0 1.2rem 0;
}
.uwa-badge {
  display: inline-block;
  background: var(--uwa-gold);
  color: var(--uwa-navy);
  font-weight: 700;
  font-size: 0.78rem;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.uwa-section-card {
  background: #ffffff;
  border: 1px solid var(--uwa-navy-l);
  border-radius: var(--radius);
  padding: 1.2rem 1.4rem;
  margin-bottom: 1rem;
  box-shadow: var(--shadow);
}
.uwa-step-badge {
  background: var(--uwa-navy);
  color: #fff;
  font-weight: 700;
  font-size: 1rem;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-right: 0.5rem;
}

/* ── Footer ─────────────────────────────────────────────────────────────── */
footer {visibility: hidden;}
.uwa-footer {
  text-align: center;
  color: var(--uwa-text-m);
  font-size: 0.78rem;
  padding: 1.5rem 0 0.5rem 0;
  border-top: 1px solid var(--uwa-navy-l);
  margin-top: 2rem;
}
.uwa-footer a { color: var(--uwa-navy); text-decoration: none; }
.uwa-footer a:hover { color: var(--uwa-gold); }

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--uwa-bg); }
::-webkit-scrollbar-thumb { background: var(--uwa-navy-l); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--uwa-navy); }
"""


def inject_uwa_theme() -> None:
    """Inject the full UWA CSS into the current page. Call once per page."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


def uwa_page_header(title: str, subtitle: str = "", icon: str = "") -> None:
    """Render a branded page header banner."""
    icon_html = f'<span style="font-size:2rem;line-height:1">{icon}</span>' if icon else ""
    st.markdown(
        f"""
        <div class="uwa-page-header">
          {icon_html}
          <div>
            <p class="header-title">{title}</p>
            <p class="header-sub">{subtitle}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def uwa_gold_bar() -> None:
    """Render a thin gold accent bar."""
    st.markdown('<div class="uwa-gold-bar"></div>', unsafe_allow_html=True)


def uwa_badge(text: str) -> None:
    st.markdown(f'<span class="uwa-badge">{text}</span>', unsafe_allow_html=True)


def uwa_footer() -> None:
    st.markdown(
        """
        <div class="uwa-footer">
          RIM Online &nbsp;|&nbsp; The University of Western Australia &nbsp;|&nbsp;
          <a href="https://www.uwa.edu.au" target="_blank">uwa.edu.au</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def uwa_sidebar_logo() -> None:
    """Render a compact UWA-branded sidebar header."""
    st.sidebar.markdown(
        f"""
        <div style="
          text-align:center;
          padding:1.2rem 0.5rem 1rem;
          border-bottom: 2px solid {UWA_GOLD};
          margin-bottom:1rem;">
          <div style="font-size:2.2rem;line-height:1;">🌾</div>
          <div style="
            font-weight:800;
            font-size:1.15rem;
            color:#ffffff;
            letter-spacing:-0.01em;
            margin-top:0.4rem;">RIM Online</div>
          <div style="
            font-size:0.73rem;
            color:rgba(255,255,255,0.65);
            margin-top:0.2rem;">Ryegrass Integrated Management</div>
          <div style="
            display:inline-block;
            background:{UWA_GOLD};
            color:{UWA_NAVY};
            font-size:0.68rem;
            font-weight:700;
            padding:0.15rem 0.55rem;
            border-radius:999px;
            margin-top:0.5rem;
            text-transform:uppercase;
            letter-spacing:0.06em;">UWA</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
