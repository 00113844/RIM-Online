"""Shared visual system for RIM Online.

Design direction
----------------
RIM exists because ryegrass seed banks *compound*. A decade of decisions either
draws the bank down or lets it run away, and the whole tool is an argument about
that one stock. So the interface is built around it: the seed-bank spine sits
above the editor on every working page and never leaves the screen.

Colour is semantic first, brand second. UWA navy and gold carry identity —
sidebar, rules, logo — but they are deliberately kept out of the data. Ryegrass
pressure is sienna (the thing you are fighting) and money is teal (deliberately
not green, so the weed and the margin can never be confused at a glance).

Type is the Archivo superfamily, using *width* rather than another weight bump
as the display signature, with IBM Plex Mono for every number so figures always
read as instrument output.
"""
from __future__ import annotations

import base64
import pathlib

import streamlit as st

# ── Tokens ────────────────────────────────────────────────────────────────────
INK        = "#101A2B"   # near-black navy: text and structure
NAVY       = "#003087"   # UWA navy: identity
NAVY_DEEP  = "#001C50"
GOLD       = "#DAAA00"   # UWA gold: identity accent, used as a hairline
PAPER      = "#F4F5F2"   # warm pale grey — stubble, not cream
CARD       = "#FFFFFF"
LINE       = "#DFE1DB"
MUTED      = "#5D6B7A"
FAINT      = "#8A96A3"

RYE        = "#A8442A"   # ryegrass pressure — the threat
RYE_SOFT   = "#E3C4B9"
MARGIN     = "#0E6E5C"   # money — teal, never green
MARGIN_SOFT = "#B9DBD3"
WARN       = "#B67E00"

# Back-compat aliases: older pages import these names.
UWA_NAVY, UWA_NAVY_D, UWA_NAVY_L = NAVY, NAVY_DEEP, LINE
UWA_GOLD, UWA_GOLD_L = GOLD, "#F0E3A8"
UWA_WHITE, UWA_BG, UWA_BG2 = CARD, PAPER, "#EAECE6"
UWA_TEXT, UWA_TEXT_M = INK, MUTED
UWA_GREEN, UWA_RED = MARGIN, RYE


_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {{
  --ink: {INK};
  --navy: {NAVY};
  --navy-deep: {NAVY_DEEP};
  --gold: {GOLD};
  --paper: {PAPER};
  --card: {CARD};
  --line: {LINE};
  --muted: {MUTED};
  --faint: {FAINT};
  --rye: {RYE};
  --rye-soft: {RYE_SOFT};
  --margin: {MARGIN};
  --margin-soft: {MARGIN_SOFT};
  --radius: 6px;
  --sans: 'Archivo', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --mono: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
}}

/* ── Base ─────────────────────────────────────────────────────────────── */
html, body, [class*="css"], .stApp {{
  font-family: var(--sans);
  color: var(--ink);
}}
.stApp {{ background: var(--paper); }}

.block-container {{
  padding-top: 3.6rem;
  padding-bottom: 4rem;
  max-width: 1500px;
}}

h1, h2, h3, h4 {{ font-family: var(--sans); color: var(--ink); letter-spacing: -0.01em; }}

/* Numbers are instrument output, everywhere. */
.rim-num, [data-testid="stMetricValue"] {{
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
}}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
  background: var(--navy);
  border-right: none;
}}
[data-testid="stSidebar"] > div:first-child {{ padding-top: 0.5rem; }}

/* Nav: quiet by default, gold rule on the active page. No forced bolding. */
[data-testid="stSidebarNav"] a {{
  border-left: 2px solid transparent;
  border-radius: 0;
  padding-left: 0.85rem;
  margin: 0.05rem 0.5rem;
  transition: background .12s ease, border-color .12s ease;
}}
[data-testid="stSidebarNav"] a span {{
  color: rgba(255,255,255,0.72);
  font-family: var(--sans);
  font-size: 0.88rem;
  font-weight: 400;
  font-stretch: 100%;
}}
[data-testid="stSidebarNav"] a:hover {{ background: rgba(255,255,255,0.06); }}
[data-testid="stSidebarNav"] a:hover span {{ color: #fff; }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{
  background: rgba(255,255,255,0.10);
  border-left-color: var(--gold);
}}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{
  color: #fff;
  font-weight: 600;
}}
/* Streamlit lists the entrypoint as "app"; it duplicates Welcome. */
[data-testid="stSidebarNav"] li:first-child {{ display: none; }}

[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stCaption {{ color: rgba(255,255,255,0.78); }}

/* ── Page header ──────────────────────────────────────────────────────── */
.rim-head {{
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding-bottom: 0.9rem;
  margin-bottom: 1.4rem;
  border-bottom: 1px solid var(--line);
  position: relative;
}}
.rim-head::after {{
  content: "";
  position: absolute;
  left: 0; bottom: -1px;
  width: 56px; height: 3px;
  background: var(--gold);
}}
.rim-step {{
  font-family: var(--mono);
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--navy);
}}
.rim-title {{
  font-size: 1.85rem;
  font-weight: 600;
  font-stretch: 118%;
  line-height: 1.15;
  margin: 0;
  color: var(--ink);
}}
.rim-sub {{ font-size: 0.95rem; color: var(--muted); margin: 0; }}

/* ── Section label ────────────────────────────────────────────────────── */
.rim-section {{
  font-family: var(--mono);
  font-size: 0.68rem;
  font-weight: 500;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: var(--faint);
  margin: 1.6rem 0 0.55rem;
  padding-bottom: 0.3rem;
  border-bottom: 1px solid var(--line);
}}

/* ── Seed-bank spine: the signature element ───────────────────────────── */
.rim-spine {{
  display: grid;
  grid-template-columns: repeat(var(--cols, 10), 1fr);
  gap: 3px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 0.85rem 0.9rem 0.7rem;
  margin-bottom: 0.9rem;
}}
.rim-spine-cell {{
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 0.3rem;
  min-width: 0;
}}
.rim-spine-bar {{
  position: relative;
  height: 58px;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: flex-end;
}}
.rim-spine-fill {{
  width: 100%;
  border-radius: 2px 2px 0 0;
  background: var(--rye);
  min-height: 3px;
  transition: height .18s ease;
}}
.rim-spine-meta {{
  display: flex;
  flex-direction: column;
  gap: 1px;
  border-top: 1px solid var(--line);
  padding-top: 0.3rem;
}}
.rim-spine-yr {{
  font-family: var(--mono);
  font-size: 0.62rem;
  color: var(--faint);
}}
.rim-spine-crop {{
  font-size: 0.7rem;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.rim-spine-val {{
  font-family: var(--mono);
  font-size: 0.68rem;
  font-weight: 500;
  color: var(--ink);
}}
.rim-spine-legend {{
  display: flex;
  gap: 1.1rem;
  align-items: baseline;
  font-size: 0.74rem;
  color: var(--muted);
  margin: -0.4rem 0 1.1rem;
}}
.rim-spine-legend b {{ font-family: var(--mono); color: var(--ink); font-weight: 500; }}

/* ── Metric row ───────────────────────────────────────────────────────── */
.rim-metrics {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 0.7rem;
  margin-bottom: 0.4rem;
}}
.rim-metric {{
  background: var(--card);
  border: 1px solid var(--line);
  border-top: 2px solid var(--accent, var(--navy));
  border-radius: var(--radius);
  padding: 0.8rem 0.95rem 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}}
.rim-metric-label {{
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--faint);
}}
.rim-metric-value {{
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
  font-size: 1.42rem;
  font-weight: 500;
  color: var(--ink);
  line-height: 1.2;
}}
.rim-metric-unit {{ font-size: 0.8rem; color: var(--muted); font-weight: 400; }}
.rim-metric-note {{ font-size: 0.72rem; color: var(--muted); }}

/* ── Controls ─────────────────────────────────────────────────────────── */
.stButton > button {{
  font-family: var(--sans);
  font-size: 0.86rem;
  font-weight: 500;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background: var(--card);
  color: var(--ink);
  padding: 0.4rem 0.9rem;
  transition: border-color .12s ease, background .12s ease;
  box-shadow: none;
}}
.stButton > button:hover {{
  border-color: var(--navy);
  background: #fff;
  color: var(--navy);
}}
.stButton > button:focus-visible {{ outline: 2px solid var(--gold); outline-offset: 1px; }}
.stButton > button[kind="primary"] {{
  background: var(--navy);
  border-color: var(--navy);
  color: #fff;
}}
.stButton > button[kind="primary"]:hover {{ background: var(--navy-deep); color: #fff; }}

/* Disabled: ghost, with a reddish cast so "you cannot do this" reads at a
   glance rather than looking like a rendering artefact. Applies to any control
   the app switches off, not just buttons. */
.stButton > button:disabled,
.stDownloadButton > button:disabled,
.stButton > button[disabled] {{
  background: #FBF4F2;
  border-color: #E4C9C1;
  border-style: dashed;
  color: #B08276;
  cursor: not-allowed;
  opacity: 1;
}}
.stButton > button:disabled:hover {{
  background: #FBF4F2;
  border-color: #E4C9C1;
  color: #B08276;
}}
/* A disabled select is a statement, not a rendering artefact. */
[data-baseweb="select"][aria-disabled="true"],
.stSelectbox [data-baseweb="select"][disabled],
div[data-testid="stSelectbox"] div[aria-disabled="true"] {{
  background: #FBF4F2;
  border-color: #E4C9C1;
  border-style: dashed;
  color: #B08276;
  cursor: not-allowed;
}}
div[data-testid="stSelectbox"] div[aria-disabled="true"] div {{ color: #B08276; }}

.rim-blocked {{
  font-size: 0.73rem;
  line-height: 1.35;
  color: #97624F;
  background: #FBF4F2;
  border-left: 2px solid #E4C9C1;
  border-radius: 0 3px 3px 0;
  padding: 0.3rem 0.5rem;
  margin-top: 0.3rem;
}}

[data-testid="stWidgetLabel"] label p {{
  font-size: 0.78rem;
  color: var(--muted);
  font-weight: 500;
}}

/* Tabs: a rule, not a pill row. */
.stTabs [data-baseweb="tab-list"] {{
  gap: 1.4rem;
  border-bottom: 1px solid var(--line);
}}
.stTabs [data-baseweb="tab"] {{
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--muted);
  padding: 0.4rem 0;
  background: transparent;
}}
.stTabs [aria-selected="true"] {{ color: var(--ink); }}
.stTabs [data-baseweb="tab-highlight"] {{ background: var(--navy); }}

/* Data editor and tables */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}}

/* Expanders as quiet containers */
[data-testid="stExpander"] {{
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--card);
}}
[data-testid="stExpander"] summary {{ font-size: 0.86rem; font-weight: 500; }}

/* Alerts: flat, left-ruled */
[data-testid="stAlert"] {{
  border-radius: var(--radius);
  border: 1px solid var(--line);
  border-left: 3px solid var(--navy);
  background: var(--card);
  color: var(--ink);
  font-size: 0.88rem;
}}

/* ── "No effect" notices ─────────────────────────────────────────────── */
.rim-ghosts {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 0.5rem 0 0.2rem;
}}
.rim-ghost {{
  display: inline-flex;
  align-items: baseline;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: #B08276;
  background: #FBF4F2;
  border: 1px dashed #E4C9C1;
  border-radius: var(--radius);
  padding: 0.2rem 0.55rem;
}}
.rim-ghost b {{
  font-family: var(--mono);
  font-weight: 500;
  font-size: 0.72rem;
  color: #97624F;
}}

/* ── Footer ───────────────────────────────────────────────────────────── */
.rim-footer {{
  margin-top: 3rem;
  padding-top: 1rem;
  border-top: 1px solid var(--line);
  font-size: 0.78rem;
  color: var(--faint);
}}
.rim-footer a {{ color: var(--muted); text-decoration: none; }}
.rim-footer a:hover {{ color: var(--navy); text-decoration: underline; }}

/* ── Sidebar brand ────────────────────────────────────────────────────── */
.rim-brand {{
  padding: 0.4rem 1rem 1.1rem;
  border-bottom: 1px solid rgba(255,255,255,0.16);
  margin-bottom: 0.6rem;
}}
.rim-brand-name {{
  font-size: 1.12rem;
  font-weight: 600;
  font-stretch: 118%;
  color: #fff;
  line-height: 1.1;
}}
.rim-brand-sub {{
  font-size: 0.7rem;
  color: rgba(255,255,255,0.6);
  margin-top: 0.18rem;
}}
.rim-brand-rule {{
  width: 34px; height: 2px;
  background: var(--gold);
  margin-top: 0.6rem;
}}
.rim-partners {{
  padding: 1rem;
  margin-top: 0.5rem;
  border-top: 1px solid rgba(255,255,255,0.16);
}}
.rim-partners-label {{
  font-family: var(--mono);
  font-size: 0.6rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.45);
  margin-bottom: 0.5rem;
}}

@media (prefers-reduced-motion: reduce) {{
  * {{ transition: none !important; animation: none !important; }}
}}

::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: #C8CCC4; border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--muted); }}
"""


# ── Injection ─────────────────────────────────────────────────────────────────
def inject_uwa_theme() -> None:
    """Inject the RIM stylesheet. Call once per page, before any content."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


# ── Page furniture ────────────────────────────────────────────────────────────
def uwa_page_header(title: str, subtitle: str = "", icon: str = "") -> None:
    """Page header: a step label, the title, and a gold rule.

    ``icon`` is accepted for backwards compatibility and ignored — the emoji
    banners it used to render competed with the data for attention.
    """
    step, _, rest = title.partition("—")
    if rest:
        eyebrow, heading = step.strip(), rest.strip()
    else:
        eyebrow, heading = "", title.strip()

    eyebrow_html = f'<span class="rim-step">{eyebrow}</span>' if eyebrow else ""
    sub_html = f'<p class="rim-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="rim-head">{eyebrow_html}'
        f'<p class="rim-title">{heading}</p>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def section(label: str) -> None:
    """A quiet, ruled section label."""
    st.markdown(f'<div class="rim-section">{label}</div>', unsafe_allow_html=True)


def metric_row(items: list[dict]) -> None:
    """A row of figures.

    Each item: ``{"label", "value", "unit"?, "note"?, "accent"?}``. ``accent``
    takes ``"rye"``, ``"margin"`` or a hex value, and colours the top rule so
    weed pressure and money are distinguishable without reading the label.
    """
    accents = {"rye": RYE, "margin": MARGIN, "navy": NAVY, "gold": GOLD}
    cells = []
    for item in items:
        accent = accents.get(item.get("accent", "navy"), item.get("accent", NAVY))
        unit = f' <span class="rim-metric-unit">{item["unit"]}</span>' if item.get("unit") else ""
        note = f'<span class="rim-metric-note">{item["note"]}</span>' if item.get("note") else ""
        cells.append(
            f'<div class="rim-metric" style="--accent:{accent}">'
            f'<span class="rim-metric-label">{item["label"]}</span>'
            f'<span class="rim-metric-value">{item["value"]}{unit}</span>'
            f"{note}</div>"
        )
    st.markdown(f'<div class="rim-metrics">{"".join(cells)}</div>', unsafe_allow_html=True)


def seedbank_spine(years, crops, seed_bank, unit: str = "seeds/m²") -> None:
    """The seed-bank spine — one cell per year, always above the editor.

    RIM is an argument about a compounding stock, so the stock stays on screen
    while you edit. Bars are scaled to the run's own peak: the shape of the
    decade is what matters, not the absolute height.
    """
    values = [max(0.0, float(v or 0.0)) for v in seed_bank]
    peak = max(values) if values else 0.0
    cells = []
    for year, crop, value in zip(years, crops, values):
        height = 0 if peak <= 0 else round(100 * value / peak)
        # Ramp toward sienna as the bank fills; gold at the low end reads as
        # "holding", not "safe".
        share = 0 if peak <= 0 else value / peak
        colour = GOLD if share < 0.25 else (WARN if share < 0.6 else RYE)
        shown = f"{value:,.0f}" if value >= 10 else f"{value:.1f}"
        cells.append(
            '<div class="rim-spine-cell">'
            f'<div class="rim-spine-bar"><div class="rim-spine-fill" '
            f'style="height:{height}%;background:{colour}"></div></div>'
            '<div class="rim-spine-meta">'
            f'<span class="rim-spine-yr">YR {year}</span>'
            f'<span class="rim-spine-crop">{crop}</span>'
            f'<span class="rim-spine-val">{shown}</span>'
            "</div></div>"
        )

    st.markdown(
        f'<div class="rim-spine" style="--cols:{len(cells)}">{"".join(cells)}</div>',
        unsafe_allow_html=True,
    )
    if values:
        direction = "falling" if values[-1] < values[0] else "rising"
        st.markdown(
            f'<div class="rim-spine-legend">'
            f"<span>Seed bank at the end of each year, {unit} — "
            f"<b>{direction}</b> across the run</span>"
            f"<span>After year 1 <b>{values[0]:,.1f}</b></span>"
            f"<span>After year {len(values)} <b>{values[-1]:,.1f}</b></span>"
            f"<span>Peak <b>{peak:,.1f}</b></span>"
            "</div>",
            unsafe_allow_html=True,
        )


def uwa_gold_bar() -> None:
    st.markdown(
        '<div style="height:3px;width:56px;background:var(--gold);margin:0.6rem 0 1rem"></div>',
        unsafe_allow_html=True,
    )


def uwa_badge(text: str) -> None:
    st.markdown(
        f'<span style="font-family:var(--mono);font-size:0.68rem;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{NAVY};border:1px solid {LINE};'
        f'border-radius:3px;padding:0.12rem 0.4rem">{text}</span>',
        unsafe_allow_html=True,
    )


def uwa_footer() -> None:
    st.markdown(
        '<div class="rim-footer">RIM Online &middot; Ryegrass Integrated Management &middot; '
        'The University of Western Australia and AHRI &middot; '
        '<a href="https://www.uwa.edu.au" target="_blank" rel="noopener">uwa.edu.au</a></div>',
        unsafe_allow_html=True,
    )


def uwa_sidebar_logo() -> None:
    """Sidebar brand block, and the AHRI mark in the partner slot below the nav."""
    st.sidebar.markdown(
        '<div class="rim-brand">'
        '<div class="rim-brand-name">RIM Online</div>'
        '<div class="rim-brand-sub">Ryegrass Integrated Management</div>'
        '<div class="rim-brand-rule"></div>'
        "</div>",
        unsafe_allow_html=True,
    )

    logo = pathlib.Path(__file__).parent.parent / "AHRI_logo.jpg"
    if logo.exists():
        encoded = base64.b64encode(logo.read_bytes()).decode()
        st.sidebar.markdown(
            '<div class="rim-partners">'
            '<div class="rim-partners-label">Developed with</div>'
            f'<img src="data:image/jpeg;base64,{encoded}" alt="AHRI" '
            'style="width:82px;height:auto;border-radius:3px">'
            "</div>",
            unsafe_allow_html=True,
        )


def ghost_notices(findings: list[dict]) -> None:
    """Render choices the model ignores as ghosted, reddish chips.

    Selecting an option the workbook gates out looks identical on screen to one
    that worked. These say plainly which ones did nothing, and cite the cell
    that decided it. Identical findings are grouped so a decision repeated
    across the run reads as one problem, not ten.
    """
    if not findings:
        return

    grouped: dict[tuple, list[int]] = {}
    for item in findings:
        key = (item["field"], str(item["choice"]), item["reason"], item["source"])
        grouped.setdefault(key, []).append(item["year"])

    chips = []
    for (field, choice, reason, source), years in grouped.items():
        if len(years) == 1:
            when = f"YR {years[0]}"
        elif len(years) >= 8:
            when = f"{len(years)} YRS"
        else:
            when = "YR " + ",".join(str(y) for y in sorted(years))
        chips.append(
            '<span class="rim-ghost" title="Excel source: '
            f'{source}"><b>{when}</b>{field}: {choice} — {reason}</span>'
        )
    st.markdown(f'<div class="rim-ghosts">{"".join(chips)}</div>', unsafe_allow_html=True)
