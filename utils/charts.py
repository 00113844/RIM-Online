"""Plotly builders for RIM Online.

One rule holds the set together: **ryegrass is sienna, money is teal.** The two
never share a hue, so a glance at any chart says which is being shown without
reading the legend. Everything else — grid, axes, fonts — is deliberately quiet
so the marks carry the page.
"""
from __future__ import annotations

import plotly.graph_objects as go

from utils.theme import FAINT, GOLD, INK, LINE, MARGIN, MARGIN_SOFT, MUTED, NAVY, RYE, RYE_SOFT

FONT = "Archivo, -apple-system, Segoe UI, sans-serif"
MONO = "IBM Plex Mono, ui-monospace, monospace"

# Income sources: one hue stepped in value, so the stack reads as one quantity
# split three ways rather than three unrelated things.
INCOME_SHADES = (NAVY, "#4A6DA8", "#9DB0CE")

# The workbook's own fixed axis limits, so two runs can be compared by eye.
# Forms_Graphs.bas: Scale_Str() and Scale_Pop().
FIXED_MARGIN_RANGE = [-200, 600]      # $/ha
FIXED_RYEGRASS_RANGE = [0, 500]       # plants/m²
FIXED_PLANTS_RANGE = [0, 500]         # plants/m²
FIXED_SEEDBANK_RANGE = [0, 25]        # seeds/m²
FIXED_WEED_COST_RANGE = [0, 100]      # $/ha
FIXED_INCOME_RANGE = [0, 600]         # $/ha


def _base(fig: go.Figure, *, height: int = 320, legend: bool = True) -> go.Figure:
    """Shared frame: no chart junk, generous margins, tabular figures."""
    fig.update_layout(
        height=height,
        font=dict(family=FONT, size=12, color=MUTED),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=28, l=8, r=8, b=8),
        hoverlabel=dict(font=dict(family=MONO, size=12), bgcolor="#fff", bordercolor=LINE),
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            font=dict(size=11), bgcolor="rgba(0,0,0,0)",
        ),
        bargap=0.3,
    )
    fig.update_xaxes(
        title=None, showgrid=False, zeroline=False,
        linecolor=LINE, ticks="outside", tickcolor=LINE, ticklen=4,
        tickfont=dict(family=MONO, size=11, color=FAINT), dtick=1,
    )
    fig.update_yaxes(
        gridcolor=LINE, zerolinecolor=LINE, zerolinewidth=1,
        tickfont=dict(family=MONO, size=11, color=FAINT),
        title_font=dict(size=11, color=FAINT),
    )
    return fig


def gross_margin_and_ryegrass_chart(df, title: str = "", fixed_scale: bool = False):
    """Gross margin against the ryegrass stand that produced it."""
    fig = go.Figure()
    fig.add_bar(
        x=df["year"], y=df["gross_margin"], name="Gross margin",
        marker_color=[MARGIN if v >= 0 else RYE for v in df["gross_margin"]],
        marker_line_width=0, hovertemplate="Year %{x}<br>$%{y:.0f}/ha<extra></extra>",
    )
    fig.add_scatter(
        x=df["year"], y=df["ryegrass_plants_m2"], name="Ryegrass",
        mode="lines+markers", yaxis="y2",
        line=dict(color=RYE, width=2), marker=dict(size=5, color=RYE),
        hovertemplate="Year %{x}<br>%{y:.1f} plants/m²<extra></extra>",
    )
    _base(fig, height=340)
    fig.update_layout(
        yaxis=dict(title="$/ha", gridcolor=LINE, zerolinecolor=MUTED, zerolinewidth=1),
        yaxis2=dict(title="plants/m²", overlaying="y", side="right",
                    showgrid=False, tickfont=dict(family=MONO, size=11, color=RYE),
                    title_font=dict(size=11, color=RYE)),
    )
    if fixed_scale:
        # Set both axes through update_layout. `secondary_y` belongs to figures
        # built with make_subplots; this one overlays yaxis2 by hand, so asking
        # for it raises. update_layout merges, so the fonts set above survive.
        fig.update_layout(
            yaxis=dict(range=FIXED_MARGIN_RANGE),
            yaxis2=dict(range=FIXED_RYEGRASS_RANGE),
        )
    return fig


def weed_cost_chart(df, title: str = "", fixed_scale: bool = False):
    """What weed control cost, year by year."""
    fig = go.Figure()
    fig.add_bar(
        x=df["year"], y=df["weed_control_cost"], name="Weed control",
        marker_color=RYE_SOFT, marker_line=dict(color=RYE, width=1),
        hovertemplate="Year %{x}<br>$%{y:.2f}/ha<extra></extra>",
    )
    _base(fig, height=280, legend=False)
    fig.update_yaxes(title="$/ha")
    if fixed_scale:
        fig.update_yaxes(range=FIXED_WEED_COST_RANGE)
    return fig


def income_breakdown_chart(df, title: str = "", fixed_scale: bool = False):
    """Where the income came from."""
    fig = go.Figure()
    for name, column, shade in zip(
        ("Grain", "Pasture & fodder", "Livestock"),
        ("income_grain", "income_pasture", "income_livestock"),
        INCOME_SHADES,
    ):
        fig.add_bar(x=df["year"], y=df[column], name=name, marker_color=shade,
                    marker_line_width=0,
                    hovertemplate=f"{name}<br>Year %{{x}}<br>$%{{y:.0f}}/ha<extra></extra>")
    _base(fig, height=280)
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="$/ha")
    if fixed_scale:
        fig.update_yaxes(range=FIXED_INCOME_RANGE)
    return fig


def seedbank_population_chart(df, title: str = "", fixed_scale: bool = False):
    """The stand and the stock behind it.

    The seed bank is drawn as a filled area because it is a *stock*; the plant
    count is a line because it is a yearly reading.
    """
    fig = go.Figure()
    fig.add_scatter(
        x=df["year"], y=df["seed_bank_end"], name="Seed bank", yaxis="y2",
        mode="lines", line=dict(color=GOLD, width=1.5),
        fill="tozeroy", fillcolor="rgba(218,170,0,0.16)",
        hovertemplate="Year %{x}<br>%{y:,.0f} seeds/m²<extra></extra>",
    )
    fig.add_scatter(
        x=df["year"], y=df["ryegrass_plants_m2"], name="Ryegrass plants",
        mode="lines+markers", line=dict(color=RYE, width=2),
        marker=dict(size=5, color=RYE),
        hovertemplate="Year %{x}<br>%{y:.1f} plants/m²<extra></extra>",
    )
    _base(fig, height=340)
    fig.update_layout(
        yaxis=dict(title="plants/m²", gridcolor=LINE),
        yaxis2=dict(title="seeds/m²", overlaying="y", side="right", showgrid=False,
                    tickfont=dict(family=MONO, size=11, color=FAINT),
                    title_font=dict(size=11, color=FAINT)),
    )
    if fixed_scale:
        fig.update_layout(
            yaxis=dict(range=FIXED_PLANTS_RANGE),
            yaxis2=dict(range=FIXED_SEEDBANK_RANGE),
        )
    return fig


def yield_comparison_chart(df, title: str = ""):
    """Potential yield against what the ryegrass left behind.

    Drawn as one bar with the loss stacked on top, so the gap *is* the penalty
    rather than something the reader has to measure between two bars.
    """
    lost = (df["yield_potential_t_ha"] - df["yield_t_ha"]).clip(lower=0)
    fig = go.Figure()
    fig.add_bar(
        x=df["year"], y=df["yield_t_ha"], name="Harvested",
        marker_color=MARGIN, marker_line_width=0,
        hovertemplate="Year %{x}<br>%{y:.2f} t/ha harvested<extra></extra>",
    )
    fig.add_bar(
        x=df["year"], y=lost, name="Lost to ryegrass",
        marker_color=RYE_SOFT, marker_line=dict(color=RYE, width=1),
        hovertemplate="Year %{x}<br>%{y:.2f} t/ha lost<extra></extra>",
    )
    _base(fig, height=320)
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="t/ha")
    return fig


def comparison_chart(series: dict[str, tuple], title: str = "", y_title: str = "$/ha"):
    """Strategy A against Strategy B on one axis.

    ``series`` maps a label to ``(years, values)``. A is navy, B is gold: two
    identities, neither of which is the ryegrass or money hue, so the comparison
    never competes with the semantics of the other charts.
    """
    fig = go.Figure()
    for (label, (years, values)), colour in zip(series.items(), (NAVY, GOLD)):
        fig.add_bar(x=years, y=values, name=label, marker_color=colour,
                    marker_line_width=0,
                    hovertemplate=f"{label}<br>Year %{{x}}<br>%{{y:.1f}}<extra></extra>")
    _base(fig, height=320)
    fig.update_layout(barmode="group")
    fig.update_yaxes(title=y_title)
    return fig
