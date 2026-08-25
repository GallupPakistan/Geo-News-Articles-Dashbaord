import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import (
    author_gap_stats, author_month_heatmap, avg_words_by_author,
    coauthor_pairs, coauthor_split, contributor_mix, explode_authors,
    get_dataframe, inject_branding, kpi_grid, new_vs_returning_authors,
    sidebar_filters, solo_co_by_author, top_authors_cumulative_share,
)

inject_branding("Authors")

df = get_dataframe()
fdf = sidebar_filters(df)

st.title("✍️ Authors")
st.caption("Who's writing, how often, and when")

if fdf.empty:
    st.info("No articles in the current filter.")
    st.stop()

exploded = explode_authors(fdf)
solo, co = coauthor_split(fdf)
one_off, repeat = contributor_mix(fdf)
n_authors = exploded["Author"].nunique()
top_author, top_author_count = exploded["Author"].value_counts().index[0], exploded["Author"].value_counts().iloc[0]
avg_per_author = len(exploded) / max(n_authors, 1)

kpi_grid([
    {"emoji": "✍️", "label": "Unique authors", "value": n_authors},
    {"emoji": "👑", "label": "Most prolific", "value": top_author,
     "sub": f"{top_author_count} article(s)"},
    {"emoji": "📊", "label": "Avg. articles / author", "value": f"{avg_per_author:.1f}"},
    {"emoji": "🤝", "label": "Solo vs co-authored", "value": f"{solo} / {co}"},
    {"emoji": "🔁", "label": "One-off vs repeat", "value": f"{one_off} / {repeat}"},
    {"emoji": "🕸️", "label": "Co-authoring pairs", "value": len(coauthor_pairs(fdf))},
])

st.divider()
st.header("🏆 Leaderboard & network")

st.subheader("Author leaderboard")
counts = fdf["Author"].value_counts().reset_index()
counts.columns = ["Author", "Articles"]

view = st.radio("View as", ["Bar", "Treemap"], horizontal=True, label_visibility="collapsed")

if view == "Bar":
    fig = px.bar(counts.sort_values("Articles"), x="Articles", y="Author", orientation="h",
                 color_discrete_sequence=["#0c2f6b"], height=max(400, 24 * len(counts)))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
else:
    fig = px.treemap(counts, path=["Author"], values="Articles", color="Articles",
                      color_continuous_scale="Blues")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=500)
    fig.update_traces(textinfo="label+value")
st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("🕸️ Collaboration network")
st.caption("Who co-writes with whom — line thickness = number of shared bylines")
pairs = coauthor_pairs(fdf)

if pairs.empty:
    st.info("No co-authored articles in the current filter.")
else:
    authors_in_net = sorted(set(pairs["Author A"]) | set(pairs["Author B"]))
    n = len(authors_in_net)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pos = {a: (np.cos(t), np.sin(t)) for a, t in zip(authors_in_net, angles)}

    edge_x, edge_y = [], []
    for _, row in pairs.iterrows():
        x0, y0 = pos[row["Author A"]]
        x1, y1 = pos[row["Author B"]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    node_weight = pairs.groupby("Author A")["Articles"].sum().add(
        pairs.groupby("Author B")["Articles"].sum(), fill_value=0
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(color="#c7cedd", width=2), hoverinfo="none",
    ))
    fig.add_trace(go.Scatter(
        x=[pos[a][0] for a in authors_in_net], y=[pos[a][1] for a in authors_in_net],
        mode="markers+text", text=authors_in_net, textposition="top center",
        textfont=dict(size=11, color="#0c2f6b"),
        marker=dict(
            size=[14 + 8 * node_weight.get(a, 1) for a in authors_in_net],
            color="#f7941e", line=dict(color="#0c2f6b", width=1.5),
        ),
        hovertemplate="%{text}<extra></extra>",
    ))
    fig.update_layout(
        showlegend=False, height=440, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, range=[-1.5, 1.5]),
        yaxis=dict(visible=False, range=[-1.5, 1.5]),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.header("📈 Output over time")

g1, g2 = st.columns(2)

with g1:
    st.subheader("🏅 Top contributors' share of output")
    st.caption("Cumulative share of articles from the top 5 authors vs. everyone else")
    share = top_authors_cumulative_share(fdf)
    if not share.empty:
        fig = px.area(share, x="Week", y="Share (%)", color="Group",
                      color_discrete_map={"Top contributors": "#f7941e", "Everyone else": "#0c2f6b"})
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough data yet.")

with g2:
    st.subheader("🆕 New vs. returning authors")
    nvr = new_vs_returning_authors(fdf)
    if not nvr.empty:
        fig = px.bar(nvr, x="Week", y="Bylines", color="Status", barmode="stack",
                     color_discrete_map={"New": "#f7941e", "Returning": "#0c2f6b"})
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough data yet.")

st.subheader("📆 Author × month activity")
heat = author_month_heatmap(fdf)
if not heat.empty:
    fig = go.Figure(go.Heatmap(
        z=heat.values, x=heat.columns, y=heat.index,
        colorscale=[[0, "#eef1f7"], [1, "#0c2f6b"]],
        hovertemplate="%{y}<br>%{x}<br>%{z} article(s)<extra></extra>",
    ))
    fig.update_layout(height=max(300, 26 * len(heat)), margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough data to build this heatmap.")

st.divider()
st.header("🧮 Writing style by author")

h1, h2, h3 = st.columns(3)

with h1:
    st.subheader("🤝 Solo vs. co-authored (top 12)")
    sc = solo_co_by_author(fdf)
    if not sc.empty:
        fig = px.bar(sc, x="Articles", y="Author", color="Type", orientation="h",
                     color_discrete_map={"Solo": "#0c2f6b", "Co-authored": "#f7941e"},
                     height=max(360, 24 * sc["Author"].nunique()))
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True)

with h2:
    st.subheader("📝 Avg. summary length (top 12)")
    aw = avg_words_by_author(fdf)
    if not aw.empty:
        fig = px.bar(aw, x="Avg words", y="Author", orientation="h",
                     color_discrete_sequence=["#f7941e"], height=max(360, 24 * len(aw)))
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

with h3:
    st.subheader("⏱️ Publishing consistency (top 8)")
    st.caption("Days between an author's consecutive pieces — lower & tighter = steadier")
    gaps = author_gap_stats(fdf)
    if not gaps.empty:
        fig = px.box(gaps, x="Gap (days)", y="Author", orientation="h",
                     color_discrete_sequence=["#0c2f6b"])
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", height=max(360, 30 * gaps["Author"].nunique()))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough repeat authors yet.")

st.divider()
st.header("🔎 Spotlight on one author")
author_choice = st.selectbox("Pick an author", sorted(fdf["Author"].unique()))
adf = fdf[fdf["Author"] == author_choice].sort_values("Publish Date", ascending=False)

m1, m2, m3 = st.columns(3)
m1.metric("📄 Articles by this author", len(adf))
m2.metric(
    "🗓️ First → latest",
    f"{adf['Publish Date'].min():%d %b} → {adf['Publish Date'].max():%d %b}" if len(adf) else "—",
)
m3.metric("📝 Avg. summary words", f"{adf['Summary (100 Words)'].fillna('').str.split().apply(len).mean():.0f}"
          if len(adf) else "—")

if len(adf) > 1:
    st.subheader(f"📈 {author_choice}'s cumulative articles")
    adf_sorted = adf.sort_values("Publish Date")
    cum = adf_sorted.groupby(adf_sorted["Publish Date"].dt.date).size().cumsum().reset_index()
    cum.columns = ["Date", "Cumulative"]
    fig = px.line(cum, x="Date", y="Cumulative", markers=True, color_discrete_sequence=["#0c2f6b"])
    fig.update_traces(fill="tozeroy", fillcolor="rgba(12,47,107,0.12)")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

st.dataframe(
    adf[["Publish Date", "Title", "Summary (100 Words)", "Article URL"]]
    .assign(**{"Publish Date": adf["Publish Date"].dt.strftime("%d %b %Y")}),
    use_container_width=True,
    height=350,
    column_config={
        "Article URL": st.column_config.LinkColumn("Article URL"),
        "Summary (100 Words)": st.column_config.TextColumn("Summary", width="large"),
    },
)
