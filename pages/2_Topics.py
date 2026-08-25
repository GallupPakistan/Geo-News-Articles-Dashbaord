import io
import re
from collections import Counter

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS

from common import (
    CUSTOM_STOP, compute_topics, explode_authors, get_dataframe, inject_branding,
    kpi_grid, sidebar_filters, topic_stats, weekday_topic_heatmap,
)

inject_branding("Topics")

df = get_dataframe()
fdf = sidebar_filters(df)

st.title("🏷️ Topics")
st.caption("What the columns are actually about — keyword frequency and auto-grouped themes")

if fdf.empty:
    st.info("No articles in the current filter.")
    st.stop()


def top_keywords(texts, n=20):
    words = []
    for t in texts:
        for w in re.findall(r"[a-zA-Z']+", str(t).lower()):
            if len(w) > 3 and w not in ENGLISH_STOP_WORDS and w not in CUSTOM_STOP:
                words.append(w)
    return Counter(words).most_common(n)


def top_bigrams(texts, n=15):
    corpus = [str(t) for t in texts if str(t).strip()]
    if not corpus:
        return []
    stop = list(ENGLISH_STOP_WORDS.union(CUSTOM_STOP))
    vec = CountVectorizer(ngram_range=(2, 2), stop_words=stop, min_df=2, max_features=500)
    try:
        X = vec.fit_transform(corpus)
    except ValueError:
        return []
    sums = np.asarray(X.sum(axis=0)).ravel()
    pairs = list(zip(vec.get_feature_names_out(), sums))
    return sorted(pairs, key=lambda p: -p[1])[:n]


kw_counts = top_keywords(fdf["Title"], 20)
n_clusters = st.slider("Number of topic clusters", 3, 10, 6)
fdf, cluster_names = compute_topics(fdf, n_clusters)

kpi_grid([
    {"emoji": "🏷️", "label": "Topic clusters", "value": len(cluster_names) if cluster_names else 0},
    {"emoji": "🔑", "label": "Unique keywords (titles)", "value": len(kw_counts)},
    {"emoji": "📌", "label": "Top keyword", "value": kw_counts[0][0].title() if kw_counts else "—",
     "sub": f"{kw_counts[0][1]} mentions" if kw_counts else ""},
])

st.divider()
st.header("🔑 Keywords")

c1, c2 = st.columns(2)

with c1:
    st.subheader("📊 Most frequent keywords (titles)")
    kw_df = pd.DataFrame(kw_counts, columns=["Keyword", "Count"])
    fig = px.bar(kw_df.sort_values("Count"), x="Count", y="Keyword", orientation="h",
                 color_discrete_sequence=["#f7941e"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("☁️ Word cloud (titles)")
    try:
        from wordcloud import WordCloud
    except ImportError:
        WordCloud = None
        st.warning(
            "Word cloud needs the `wordcloud` package — run "
            "`pip install wordcloud` in this project's environment, then "
            "reload the page.",
            icon="⚠️",
        )

    if WordCloud is not None:
        if kw_counts:
            wc = WordCloud(width=800, height=420, background_color=None, mode="RGBA",
                            colormap="Blues", prefer_horizontal=0.9).generate_from_frequencies(dict(kw_counts))
            buf = io.BytesIO()
            wc.to_image().save(buf, format="PNG")
            st.image(buf.getvalue(), use_container_width=True)
        else:
            st.info("Not enough text to build a word cloud.")

st.subheader("🔗 Most common two-word phrases")
bigrams = top_bigrams(fdf["Title"].fillna("") + " " + fdf["Summary (100 Words)"].fillna(""))
if bigrams:
    bg_df = pd.DataFrame(bigrams, columns=["Phrase", "Count"])
    fig = px.bar(bg_df.sort_values("Count"), x="Count", y="Phrase", orientation="h",
                 color_discrete_sequence=["#0c2f6b"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough repeated phrases in the current filter.")

st.divider()
st.header("🧩 Topic clusters")

if cluster_names:
    topic_counts = fdf["Topic"].value_counts().reset_index()
    topic_counts.columns = ["Topic", "Articles"]

    st.subheader("🥧 Topic share")
    fig = px.pie(topic_counts, names="Topic", values="Articles", hole=0.45,
                 color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_traces(textinfo="percent")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=440,
                       legend=dict(orientation="h", y=-0.3, font=dict(size=9)))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("📐 Topic stats — size, depth & diversity")
    tstats = topic_stats(fdf)
    s1, s2 = st.columns(2)
    with s1:
        fig = px.bar(tstats.sort_values("Avg title words"), x="Avg title words", y="Topic",
                     orientation="h", color_discrete_sequence=["#f7941e"])
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", title="Avg. title length by topic")
        st.plotly_chart(fig, use_container_width=True)
    with s2:
        fig = px.bar(tstats.sort_values("Unique authors"), x="Unique authors", y="Topic",
                     orientation="h", color_discrete_sequence=["#0c2f6b"])
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", title="Unique authors writing on each topic")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("🗓️ Weekday × topic heatmap")
    st.caption("Which days each theme tends to get covered")
    wt = weekday_topic_heatmap(fdf)
    fig = go.Figure(go.Heatmap(
        z=wt.values, x=wt.columns, y=wt.index,
        colorscale=[[0, "#eef1f7"], [1, "#f7941e"]],
        hovertemplate="%{y}<br>%{x}<br>%{z} article(s)<extra></extra>",
    ))
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=80), xaxis=dict(tickangle=-30))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("🌡️ Author × Topic heatmap")
    exploded = explode_authors(fdf)
    pivot = pd.crosstab(exploded["Author"], exploded["Topic"])
    top_authors = exploded["Author"].value_counts().head(15).index
    pivot = pivot.loc[pivot.index.intersection(top_authors)]

    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale=[[0, "#eef1f7"], [1, "#0c2f6b"]],
        hovertemplate="%{y}<br>%{x}<br>%{z} article(s)<extra></extra>",
    ))
    fig.update_layout(
        height=max(320, 26 * len(pivot)), margin=dict(l=10, r=10, t=10, b=80),
        xaxis=dict(tickangle=-30),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("🌊 Author → Topic flow")
    st.caption("Editorial concentration — which top authors feed which themes")
    flow_authors = exploded["Author"].value_counts().head(10).index
    flow = exploded[exploded["Author"].isin(flow_authors)]
    links = flow.groupby(["Author", "Topic"]).size().reset_index(name="count")

    authors_list = sorted(links["Author"].unique())
    topics_list = sorted(links["Topic"].unique())
    nodes = authors_list + topics_list
    node_idx = {n: i for i, n in enumerate(nodes)}

    palette = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel
    author_color = {a: palette[i % len(palette)] for i, a in enumerate(authors_list)}
    node_colors = [author_color[a] for a in authors_list] + ["#0c2f6b"] * len(topics_list)
    link_colors = [author_color[a].replace("rgb", "rgba")[:-1] + ",0.55)" if author_color[a].startswith("rgb")
                   else author_color[a] for a in links["Author"]]

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            label=nodes, pad=20, thickness=18,
            color=node_colors,
            line=dict(color="white", width=0.5),
        ),
        link=dict(
            source=links["Author"].map(node_idx),
            target=links["Topic"].map(node_idx),
            value=links["count"],
            color=link_colors,
            hovertemplate="%{source.label} → %{target.label}<br>%{value} article(s)<extra></extra>",
        ),
        textfont=dict(size=13, color="#0c2f6b", family="Arial, sans-serif"),
    ))
    fig.update_layout(
        height=max(480, 32 * len(nodes)), margin=dict(l=10, r=140, t=10, b=10),
        font=dict(size=13, color="#0c2f6b"),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough articles in the current filter to build topic clusters.")

st.divider()

if "Topic" in fdf.columns and fdf["Topic"].notna().any():
    st.header("📚 Browse by topic")
    topic_choice = st.selectbox("Topic cluster", sorted(fdf["Topic"].dropna().unique()))
    tdf = fdf[fdf["Topic"] == topic_choice].sort_values("Publish Date", ascending=False)
    st.dataframe(
        tdf[["Publish Date", "Title", "Author", "Article URL"]]
        .assign(**{"Publish Date": tdf["Publish Date"].dt.strftime("%d %b %Y")}),
        use_container_width=True,
        height=350,
        column_config={"Article URL": st.column_config.LinkColumn("Article URL")},
    )
