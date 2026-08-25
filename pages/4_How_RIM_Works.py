from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from utils.theme import inject_uwa_theme, section, uwa_footer, uwa_page_header, uwa_sidebar_logo

st.set_page_config(page_title="How RIM works | RIM Online", page_icon="🌾", layout="wide")

inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Guide — How RIM works",
    subtitle="The idea behind the model, and how to drive the tool. About ten minutes.",
)

st.markdown("""
<style>
[data-testid="stMain"] p, [data-testid="stMain"] li { max-width: 68ch; }
[data-testid="stMain"] h3 {
  font-size: 1.06rem; font-weight: 600; margin: 1.4rem 0 0.3rem;
  color: var(--ink); letter-spacing: -0.005em;
}
.rim-lead {
  font-size: 1.06rem; line-height: 1.6; color: var(--muted); max-width: 62ch;
}
.rim-keypoint {
  background: var(--card); border: 1px solid var(--line);
  border-left: 3px solid var(--gold); border-radius: var(--radius);
  padding: 0.9rem 1.15rem; margin: 1rem 0; max-width: 68ch;
}
.rim-keypoint b { color: var(--ink); }
.rim-tbl { width: 100%; border-collapse: collapse; font-size: 0.9rem; margin: 0.6rem 0 1rem; }
.rim-tbl th {
  text-align: left; font-size: 0.68rem; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--faint); font-weight: 500; padding: 0 1rem 0.45rem 0;
  border-bottom: 1px solid var(--line);
}
.rim-tbl td { padding: 0.55rem 1rem 0.55rem 0; border-bottom: 1px solid var(--edge-soft);
  vertical-align: top; }
.rim-tbl td:first-child { font-weight: 500; white-space: nowrap; }
.rim-tbl td:last-child { color: var(--muted); padding-right: 0; }
.rim-fig { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 1.2rem 1rem 0.8rem; overflow-x: auto; margin: 0.8rem 0 0.5rem; }
.rim-fig svg { display: block; margin: 0 auto; width: 100%; max-width: 880px; height: auto; }
.rim-cap { font-size: 0.84rem; color: var(--muted); max-width: 68ch; margin-bottom: 1.2rem; }
</style>
""", unsafe_allow_html=True)

# ── 1. The one idea ───────────────────────────────────────────────────────────
st.markdown("""
<p class="rim-lead">
RIM is not a spray calculator. It is an argument about a <b>seed bank</b> — the ryegrass
seed sitting in your soil — and what a decade of decisions does to it.
</p>

<div class="rim-keypoint">
<b>The one idea.</b> Every ryegrass plant that sets seed this spring is next autumn's
problem, and the autumn after that. A paddock either draws its seed bank down over the
years or lets it compound. Almost nothing you can do in a single season matters as much
as which of those two you are on.
</div>

That is why the tool asks for ten years rather than one, and why the strip of bars across
the top of the Strategy page — the <b>seed bank spine</b> — is the first thing you see. It
is the number the whole model is about.
""", unsafe_allow_html=True)

# ── 2. Cohorts ────────────────────────────────────────────────────────────────
section("Why timing beats intensity")

st.markdown("""
Ryegrass does not all come up at once. It emerges in **five flushes** through autumn and
winter, and this is the single most important thing to understand about the model.

Each control you apply only catches what has **already emerged**. A pre-emergent sprayed at
seeding cannot touch a plant that comes up six weeks later. A post-emergent catches
everything standing on the day, and nothing still in the soil.
""")

st.markdown("""
<div class="rim-fig">
<svg viewBox="0 0 880 320" width="880" height="320" role="img" aria-label="A season timeline. Five ryegrass flushes emerge at different times. The knock-down and seeding catch only the first flush; the pre-emergent covers the early flushes; the post-emergent catches everything standing on the day but misses the last flush, which survives to set seed.">
  <defs>
    <marker id="gt" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#8A96A3"/>
    </marker>
  </defs>
  <!-- time axis -->
  <line x1="60" y1="272" x2="830" y2="272" stroke="#DFE1DB" stroke-width="1" marker-end="url(#gt)"/>
  <text x="62" y="292" font-family="IBM Plex Mono, monospace" font-size="11" fill="#8A96A3">break of season</text>
  <text x="470" y="292" font-family="IBM Plex Mono, monospace" font-size="11" fill="#8A96A3">winter</text>
  <!-- control markers -->
  <g stroke="#003087" stroke-dasharray="3 3" stroke-width="1">
    <line x1="120" y1="42" x2="120" y2="268"/>
    <line x1="500" y1="42" x2="500" y2="268"/>
    <line x1="650" y1="42" x2="650" y2="268"/>
    <line x1="780" y1="42" x2="780" y2="268"/>
  </g>
  <g font-family="Archivo, sans-serif" font-size="11.5" fill="#003087" text-anchor="middle">
    <text x="120" y="34">knock-down</text><text x="120" y="20" font-size="10" fill="#8A96A3">and seeding</text>
    <text x="500" y="34">post-emergent</text>
    <text x="650" y="34">spring option</text>
    <text x="780" y="34">harvest</text>
  </g>
  <!-- pre-emergent band -->
  <rect x="120" y="46" width="330" height="206" fill="#003087" opacity="0.05"/>
  <text x="285" y="62" font-family="Archivo, sans-serif" font-size="11.5" fill="#003087" text-anchor="middle">pre-emergent active in the soil</text>
  <!-- flushes -->
  <g font-family="Archivo, sans-serif" font-size="11.5" fill="#5D6B7A">
    <rect x="120" y="80"  width="710" height="15" rx="2" fill="#A8442A" opacity="0.85"/>
    <text x="836" y="92" fill="#101A2B" font-size="11">5%</text>
    <text x="16" y="92">flush 1</text>
    <rect x="215" y="112" width="615" height="15" rx="2" fill="#A8442A" opacity="0.75"/>
    <text x="836" y="124" fill="#101A2B" font-size="11">35%</text>
    <text x="16" y="124">flush 2</text>
    <rect x="310" y="144" width="520" height="15" rx="2" fill="#A8442A" opacity="0.65"/>
    <text x="836" y="156" fill="#101A2B" font-size="11">40%</text>
    <text x="16" y="156">flush 3</text>
    <rect x="410" y="176" width="420" height="15" rx="2" fill="#A8442A" opacity="0.55"/>
    <text x="836" y="188" fill="#101A2B" font-size="11">35%</text>
    <text x="16" y="188">flush 4</text>
    <rect x="560" y="208" width="270" height="15" rx="2" fill="#DAAA00" opacity="0.95"/>
    <text x="836" y="220" fill="#101A2B" font-size="11">15%</text>
    <text x="16" y="220">flush 5</text>
  </g>
  <text x="566" y="243" font-family="Archivo, sans-serif" font-size="11.5" fill="#97624F">
    emerges after the post-emergent — survives to set seed
  </text>
</svg>
</div>
<p class="rim-cap">
Flush 5 is the one that gets away. It comes up after the post-emergent has been and gone,
so nothing between seeding and harvest touches it. That is why late-season options —
spring topping, crop-topping, harvest weed seed control — exist at all.
</p>
""", unsafe_allow_html=True)

st.markdown("""
<div class="rim-keypoint">
<b>Read the percentages carefully.</b> Each figure is the share of the seed <i>still left in
the bank</i>, not of the original. Flush 1 takes 5% of the bank; flush 2 takes 35% of what
remains after that, and so on. A big bank therefore puts up big flushes all season.
</div>

Those fractions change with how you establish the crop. A tickle or a full-cut seeding
stirs the soil and brings more up early — the second flush rises from 35% to 60% — which
is a real tactic: <b>bring the weed up on purpose, then kill it</b>, rather than leaving it
in the soil to emerge behind your herbicide.
""", unsafe_allow_html=True)

# ── 3. What each decision does ────────────────────────────────────────────────
section("What each decision actually does")

st.markdown("""
<table class="rim-tbl">
<thead><tr><th>Decision</th><th>When it acts</th><th>What to know</th></tr></thead>
<tbody>
<tr><td>Crop or pasture</td><td>All season</td>
<td>Decides which of the choices below the model can even use, and how hard the crop
competes with the ryegrass.</td></tr>
<tr><td>Sowing time</td><td>At the break</td>
<td>Sowing later lets more ryegrass emerge before you seed, so you can kill it first — but
the crop yields less. This is the central trade-off in the model.</td></tr>
<tr><td>Sowing system, rate</td><td>At the break</td>
<td>A full-cut kills emerged plants and stirs up more seed. A high seeding rate makes the
crop compete harder, which cuts how much seed the surviving ryegrass sets.</td></tr>
<tr><td>Tillage</td><td>Before sowing</td>
<td>A tickle brings seed up early. A mouldboard plough buries it deep.</td></tr>
<tr><td>Knock-down</td><td>Before sowing</td>
<td><b>Only counts if you sow delayed.</b> With dry or wet sowing there is no gap between
spraying and seeding, so the seeding pass already accounts for those plants.</td></tr>
<tr><td>Pre-emergent</td><td>Soil, early season</td>
<td>Works on the flushes that come up while it is still active — roughly the first three.</td></tr>
<tr><td>Post-emergent</td><td>Mid season</td>
<td>Catches everything standing on the day. Misses whatever emerges afterwards.</td></tr>
<tr><td>Spring option</td><td>Before seed set</td>
<td>Hay, silage, manuring, topping and swathing all cut seed production, in that rough
order of severity.</td></tr>
<tr><td>Grazing</td><td>Through the season</td>
<td>Pasture years only. A crop is not grazed.</td></tr>
<tr><td>Harvest control</td><td>At harvest</td>
<td>Acts on <b>newly set seed passing through the header only</b> — seed already shed on the
ground is beyond reach.</td></tr>
</tbody></table>
""", unsafe_allow_html=True)

# ── 4. Competition ────────────────────────────────────────────────────────────
section("Competition is a control too")

st.markdown("""
How much seed a surviving ryegrass plant sets depends on how crowded it is. A thicker,
more competitive crop suppresses seed set directly — which is why the high seeding rate
option earns its cost even though it kills nothing.

Not all survivors are equal, either. A plant that came up with the crop competes fully; one
that emerged weeks later is small and shaded and contributes little:
""")

st.markdown("""
<table class="rim-tbl">
<thead><tr><th>Flush</th><th>How much it competes</th><th></th></tr></thead>
<tbody>
<tr><td>Flush 1</td><td>100%</td><td>Emerged with the crop</td></tr>
<tr><td>Flush 2</td><td>30%</td><td></td></tr>
<tr><td>Flush 3</td><td>10%</td><td></td></tr>
<tr><td>Flush 4</td><td>2%</td><td>Barely registers</td></tr>
</tbody></table>

<p class="rim-cap">Figures for dry or wet sowing. Sow later and the later flushes emerge
nearer the crop, so they count for more — another reason sowing time matters so much.</p>
""", unsafe_allow_html=True)

# ── 5. Working through the tool ───────────────────────────────────────────────
section("Working through the tool")

st.markdown("""
### 1 · Paddock profile
Describe the paddock once — yields, prices, interest and tax, and the starting seed bank.
Everything else is measured against this. You only need to revisit it when the paddock or
the prices change.

### 2 · Strategy
Set what happens in each of the ten years. Edit quickly in the grid, or open **Edit one
year** below it for a guided view where choices the model cannot use are switched off with
the reason shown.

### 3 · Results
Economics, population, yields and the raw tables. Watch the seed bank spine as you edit —
if it climbs year on year, the strategy is losing regardless of what this year's gross
margin says.

### Comparing two strategies
Build one plan, press **Hold as A**. Change it, press **Hold as B**. Every results page then
shows them side by side. **Release** clears both.
""")

st.markdown("""
<div class="rim-keypoint">
<b>If results do not appear</b>, the plan contains a decision the model cannot act on —
grazing on a crop, say, or a knock-down before dry sowing. The Strategy page lists each
one with the reason and a button to clear them. Results are withheld deliberately: numbers
from a plan the model half-ignores look convincing while answering a different question.
</div>
""", unsafe_allow_html=True)

# ── 6. Saving and loading ─────────────────────────────────────────────────────
section("Saving and loading your work")

st.markdown("""
<div class="rim-keypoint">
<b>Read this before you spend an hour on a plan.</b> Slots live in your browser session
only. Closing the tab, refreshing, or the app restarting will clear them. To keep work,
save it to a <b>file</b>.
</div>

### Slots — quick, temporary
<table class="rim-tbl">
<thead><tr><th>Slot type</th><th>Where</th><th>What it holds</th></tr></thead>
<tbody>
<tr><td>Profile slots 1–4</td><td>Paddock profile page</td>
<td>The paddock details, prices and options <i>together</i>, as one bundle.</td></tr>
<tr><td>Strategy slots 1–6</td><td>Strategy page</td>
<td>The ten-year plan only. Not the paddock it was built for.</td></tr>
<tr><td>Default strategy</td><td>Strategy page</td>
<td>Read-only starting point. Load it to begin again; you cannot save over it.</td></tr>
</tbody></table>

Use slots to try a variation without losing what you had: save to a slot, experiment, load
it back if the experiment was worse.

### Files — permanent, portable
Both pages have a **Keep this work** panel.

- **Save to a file** downloads everything as one `.rim.json` — the paddock profile, prices,
  options, the current ten-year plan, *and* every slot you have filled.
- **Load a saved file** restores all of it. Drop the file on the uploader.

Files are how you keep a plan between sessions, move it to another computer, or send it to
a colleague. The file is plain text, so it will still open years from now.
""", unsafe_allow_html=True)

st.markdown("""
<table class="rim-tbl">
<thead><tr><th>If you want to…</th><th>Do this</th></tr></thead>
<tbody>
<tr><td>Try a variation, keep the original</td><td>Save to a strategy slot, then edit freely</td></tr>
<tr><td>Compare two plans side by side</td><td>Hold as A, edit, Hold as B</td></tr>
<tr><td>Stop for the day</td><td><b>Save to a file</b> — slots will not survive</td></tr>
<tr><td>Send a scenario to someone</td><td>Save to a file and email the <code>.rim.json</code></td></tr>
<tr><td>Start over</td><td>Load the default strategy, or Reset all on the profile page</td></tr>
</tbody></table>
""", unsafe_allow_html=True)

# ── 7. Where to go next ───────────────────────────────────────────────────────
section("Where to go next")

left, right = st.columns(2)
with left:
    st.page_link("pages/1_Paddock_Profile.py", label="Start with the paddock profile")
    st.page_link("pages/2_Strategy.py", label="Build a ten-year strategy")
with right:
    st.page_link("pages/3_Results_Population.py", label="See what happens to the seed bank")
    st.page_link("pages/4_Export.py", label="Export a report")

st.info(
    "**About the numbers.** The ryegrass population model has been rebuilt to match the "
    "original RIM-2013b Excel workbook exactly. The yield and economic calculations are "
    "still being ported, so gross margins should be read as indicative for now.",
    icon=None,
)

uwa_footer()
