from __future__ import annotations

import plotly.graph_objects as go


def gross_margin_and_ryegrass_chart(df, title: str, fixed_scale: bool = False):
    fig = go.Figure()
    fig.add_bar(x=df["year"], y=df["gross_margin"], name="Gross margin ($/ha)", marker_color="#2E7D32")
    fig.add_scatter(
        x=df["year"],
        y=df["ryegrass_plants_m2"],
        name="Ryegrass plants/m²",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color="#8D6E63", width=3),
    )

    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Gross margin ($/ha)",
        yaxis2=dict(title="Plants/m²", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, l=40, r=50, b=30),
    )

    if fixed_scale:
        fig.update_yaxes(range=[-200, 600])
        fig.update_layout(yaxis2=dict(range=[0, 500], overlaying="y", side="right", title="Plants/m²"))
    return fig


def weed_cost_chart(df, title: str, fixed_scale: bool = False):
    fig = go.Figure()
    fig.add_bar(x=df["year"], y=df["weed_control_cost"], marker_color="#7CB342", name="Weed control cost")
    fig.update_layout(title=title, xaxis_title="Year", yaxis_title="Cost ($/ha)", margin=dict(t=60, l=40, r=20, b=30))
    if fixed_scale:
        fig.update_yaxes(range=[0, 100])
    return fig


def income_breakdown_chart(df, title: str, fixed_scale: bool = False):
    fig = go.Figure()
    fig.add_bar(x=df["year"], y=df["income_grain"], name="Grain", marker_color="#1B5E20")
    fig.add_bar(x=df["year"], y=df["income_pasture"], name="Pasture/Fodder", marker_color="#66BB6A")
    fig.add_bar(x=df["year"], y=df["income_livestock"], name="Livestock", marker_color="#A5D6A7")
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Income ($/ha)",
        barmode="stack",
        margin=dict(t=60, l=40, r=20, b=30),
    )
    if fixed_scale:
        fig.update_yaxes(range=[0, 600])
    return fig


def seedbank_population_chart(df, title: str, fixed_scale: bool = False):
    fig = go.Figure()
    fig.add_scatter(
        x=df["year"],
        y=df["ryegrass_plants_m2"],
        mode="lines+markers",
        name="Plants/m²",
        line=dict(color="#6D4C41", width=3),
    )
    fig.add_scatter(
        x=df["year"],
        y=df["seed_bank_end"],
        mode="lines+markers",
        name="Seed bank (seeds/m²)",
        yaxis="y2",
        line=dict(color="#2E7D32", width=3),
    )
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Plants/m²",
        yaxis2=dict(title="Seeds/m²", overlaying="y", side="right"),
        margin=dict(t=60, l=40, r=50, b=30),
    )
    if fixed_scale:
        fig.update_yaxes(range=[0, 500])
        fig.update_layout(yaxis2=dict(range=[0, 25], overlaying="y", side="right", title="Seeds/m²"))
    return fig


def yield_comparison_chart(df, title: str):
    fig = go.Figure()
    fig.add_bar(x=df["year"], y=df["yield_potential_t_ha"], name="Potential yield", marker_color="#AED581")
    fig.add_bar(x=df["year"], y=df["yield_t_ha"], name="Actual yield", marker_color="#43A047")
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Yield (t/ha)",
        barmode="group",
        margin=dict(t=60, l=40, r=20, b=30),
    )
    return fig
