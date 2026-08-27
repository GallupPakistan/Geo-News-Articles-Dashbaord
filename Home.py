"""Geo News — Opinions Analytics
A single-page, 4-tab dashboard (Overview / Classification Trends /
Content & Categories / Authors & Sources), restructured around
auto-classified article categories rather than raw publishing volume.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import (
    author_contribution_table, category_author_diversity, category_distribution,
    category_month_trend, category_themes, classify_articles, explode_authors,
    kpi_grid, load_data, source_distribution,
)

# ── Page config + theme ─────────────────────────────────────────────────
st.set_page_config(page_title="Geo News — Opinions Analytics", page_icon="📰", layout="wide")

INK = "#1c2333"
ACCENT = "#0d9488"       # teal — primary accent
ACCENT_2 = "#f59e0b"     # amber — secondary accent
PALETTE = ["#0d9488", "#f59e0b", "#6366f1", "#ef4444", "#0ea5e9", "#a855f7", "#84cc16", "#ec4899"]

st.markdown(f"""
<style>
#MainMenu, footer {{visibility: hidden;}}
[data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
[data-testid="stMain"] {{ background: #f4f6f8; }}
.block-container {{ padding-top: 1.2rem; max-width: 1300px; }}

section[data-testid="stSidebar"] {{ background-color: {INK}; }}
section[data-testid="stSidebar"] * {{ color: #e7eaf3 !important; }}
section[data-testid="stSidebar"] .stCheckbox label p {{ font-size: 0.85rem; }}

/* Top tab bar styled as pills, like the reference dashboard's nav */
[data-testid="stTabs"] {{
    background: #ffffff; padding: 6px; border-radius: 12px;
    border: 1px solid #e5e8ee; margin-bottom: 6px;
}}
[data-testid="stTabs"] [role="tablist"] {{ gap: 6px; }}
[data-testid="stTab"] {{
    height: 42px; border-radius: 8px; padding: 0 18px; font-weight: 600;
    color: {INK}; background: transparent;
}}
[data-testid="stTab"][aria-selected="true"] {{
    background: {ACCENT} !important;
}}
[data-testid="stTab"][aria-selected="true"] p {{ color: white !important; }}
div[data-testid="stMetric"] {{
    background: white; border-radius: 12px; padding: 12px 16px;
    border: 1px solid #e5e8ee; box-shadow: 0 1px 2px rgba(20,20,40,0.04);
}}
h1, h2, h3 {{ color: {INK}; }}
.card {{ background: white; border-radius: 12px; padding: 16px 18px; border: 1px solid #e5e8ee;
         box-shadow: 0 1px 2px rgba(20,20,40,0.04); margin-bottom: 4px; }}
.card h4 {{ margin-top: 0; margin-bottom: 10px; font-size: 0.95rem; color: {INK}; }}

/* Top filter bar — light gray tray holding individual white dropdown cards,
   matching the Gallup-style reference layout. Targets containers created
   with st.container(border=True, key="...filters") in Home.py. */
div[class*="st-key-"][class*="_filters"] {{
    background: #eef0f4 !important; border-radius: 10px !important;
    border: none !important; padding: 14px 10px 4px 10px !important; margin-bottom: 14px !important;
}}
div[data-testid="stSelectbox"], div[data-testid="stMultiSelect"], div[data-testid="stTextInput"] {{
    background: white; border-radius: 8px; border: 1px solid #e0e3ea;
    padding: 8px 12px 4px 12px;
}}
div[data-testid="stSelectbox"] label p, div[data-testid="stMultiSelect"] label p,
div[data-testid="stTextInput"] label p {{
    font-weight: 600; font-size: 0.78rem; color: #5b6472; text-transform: uppercase;
    letter-spacing: 0.03em;
}}
</style>
""", unsafe_allow_html=True)


def clean_chart(fig, h=None, legend_bottom=False):
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color=INK),
    )
    if h:
        fig.update_layout(height=h)
    if legend_bottom:
        fig.update_layout(legend=dict(orientation="h", y=-0.2))
    return fig


# ── Data + classification ──────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state["df"] = load_data(None)
df = classify_articles(st.session_state["df"])

all_categories = sorted(df["Category"].unique())
authors = sorted(explode_authors(df)["Author"].unique())

# ── Sidebar: branding + Classification checklist (Gallup-style) ──────────
# Mirrors the reference Power BI dashboard's left-hand "Classification"
# checklist — unlike a multiselect, every category gets its own checkbox,
# and the choice applies globally across all 4 tabs below.
with st.sidebar:
    st.image("assets/geo_logo.png", width=90)
    st.markdown("### Geo News — Opinions")
    st.caption("OP-ED articles analytics")
    st.divider()
    st.markdown("#### Classification")
    st.caption("Uncheck a category to hide it across every tab.")
    selected_categories = []
    for cat in all_categories:
        if st.checkbox(cat, value=True, key=f"sb_cat_{cat}"):
            selected_categories.append(cat)
    if not selected_categories:
        st.warning("Select at least one category to see data.", icon="⚠️")
        selected_categories = all_categories

df = df[df["Category"].isin(selected_categories)].copy()

col_logo, col_title = st.columns((1, 8))
with col_logo:
    st.image("assets/geo_logo.png", width=64)
with col_title:
    st.title("Opinions — Editorial Analytics")
    st.caption("Classification, categories, language and author breakdown of Geo News opinion articles")

tab_overview, tab_class, tab_content, tab_authors = st.tabs(
    ["Overview", "Classification Trends", "Content & Categories", "Authors & Sources"]
)

# ══════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════
with tab_overview:
    fdf = df.copy()

    if fdf.empty:
        st.info("No articles match the current filters.")
        st.stop()

    dist = category_distribution(fdf)
    top_cat = dist.iloc[0]["Category"] if not dist.empty else "—"
    span = f'{fdf["Publish Date"].min():%d %b %Y} – {fdf["Publish Date"].max():%d %b %Y}'

    kpi_grid([
        {"emoji": "📰", "label": "Articles", "value": str(len(fdf))},
        {"emoji": "🏷️", "label": "Categories covered", "value": str(dist["Category"].nunique())},
        {"emoji": "✍️", "label": "Authors", "value": str(explode_authors(fdf)["Author"].nunique())},
        {"emoji": "🏆", "label": "Top category", "value": top_cat},
        {"emoji": "🗓️", "label": "Coverage window", "value": span},
    ])

    st.write("")
    st.markdown('<div class="card"><h4>Share of coverage by category</h4>', unsafe_allow_html=True)
    fig = px.pie(dist, names="Category", values="Articles", hole=0.55,
                 color_discrete_sequence=PALETTE)
    fig.update_traces(textinfo="percent")
    st.plotly_chart(clean_chart(fig, h=380, legend_bottom=True), use_container_width=True,
                     config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TAB 2 — CLASSIFICATION TRENDS
# (Category IS the classification here — so this tab ranks and compares
# categories against each other, rather than repeating the same category
# breakdown against a day/month axis.)
# ══════════════════════════════════════════════════════════════════════
with tab_class:
    fdf = df.copy()

    if fdf.empty:
        st.info("No articles match the current filters.")
        st.stop()

    dist = category_distribution(fdf)

    st.markdown('<div class="card"><h4>Top classification trend</h4>', unsafe_allow_html=True)
    top_n = st.slider("Number of categories to trend", 3, min(10, fdf["Category"].nunique()),
                       min(6, fdf["Category"].nunique()))
    trend = category_month_trend(fdf, top_n=top_n)

    if trend.empty or trend["Month"].nunique() < 2:
        st.info("Not enough months of data in the current filter to draw a trend line yet — "
                "widen the date range or clear some filters.")
    else:
        fig = px.line(trend, x="Month", y="Share (%)", color="Category", markers=True,
                      text="Share (%)", color_discrete_sequence=PALETTE)
        fig.update_traces(line=dict(width=2.5), marker=dict(size=7),
                           texttemplate="%{text}%", textposition="top center",
                           textfont=dict(size=10))
        fig.update_layout(legend=dict(orientation="h", y=1.18, x=0, font=dict(size=11)),
                           xaxis_title=None, yaxis_title="Share of month's articles (%)")
        st.plotly_chart(clean_chart(fig, h=460), use_container_width=True, config={"displayModeBar": False})
        st.caption("Share of that month's articles falling in each category. "
                   "Use the Categories filter above to focus on specific ones.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="card"><h4>Classification ranking (share of all articles)</h4>',
                unsafe_allow_html=True)
    fig = px.bar(dist.sort_values("Share (%)"), x="Share (%)", y="Category", orientation="h",
                 text="Share (%)", color_discrete_sequence=[ACCENT])
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    st.plotly_chart(clean_chart(fig, h=420), use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="card"><h4>Unique authors per category</h4>', unsafe_allow_html=True)
    st.caption("Is this classification driven by one voice, or many?")
    div = category_author_diversity(fdf)
    fig = px.bar(div.sort_values("Unique authors"), x="Unique authors", y="Category",
                 orientation="h", color_discrete_sequence=[ACCENT_2])
    st.plotly_chart(clean_chart(fig, h=380), use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TAB 3 — CONTENT & CATEGORIES
# ══════════════════════════════════════════════════════════════════════
with tab_content:
    with st.container(border=True, key="content_filters"):
        sf1, sf2 = st.columns((2, 2))
        with sf1:
            content_search = st.text_input("Search title / summary", key="content_search")
        with sf2:
            content_authors = st.multiselect("Author", authors, default=[], key="content_authors")

    fdf = df.copy()
    if content_search:
        term = content_search.lower()
        fdf = fdf[
            fdf["Title"].str.lower().str.contains(term, na=False)
            | fdf["Summary (100 Words)"].str.lower().str.contains(term, na=False)
        ]
    if content_authors:
        fdf = fdf[fdf["Author"].apply(lambda a: any(x in a for x in content_authors))]

    if fdf.empty:
        st.info("No articles match the current filters.")
        st.stop()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    cat_pick = st.selectbox("Themes covered in", sorted(fdf["Category"].unique()))
    themes = category_themes(fdf, cat_pick)
    if themes.empty:
        st.info(f"Not enough repeated phrasing in **{cat_pick}** articles yet to surface distinct themes.")
    else:
        fig = px.bar(themes.sort_values("Share (%)"), x="Share (%)", y="Theme", orientation="h",
                     text="Share (%)", color_discrete_sequence=[ACCENT])
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        st.plotly_chart(clean_chart(fig, h=340), use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown(f'<div class="card"><h4>Articles in {cat_pick}</h4>', unsafe_allow_html=True)
    cat_articles = fdf[fdf["Category"] == cat_pick][["Publish Date", "Title", "Author"]]
    st.dataframe(cat_articles.sort_values("Publish Date", ascending=False),
                 use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("View all articles (every category)"):
        st.dataframe(
            fdf[["Publish Date", "Title", "Author", "Category"]].sort_values("Publish Date", ascending=False),
            use_container_width=True, hide_index=True,
        )

    st.write("")
    st.markdown('<div class="card"><h4>Word cloud</h4>', unsafe_allow_html=True)
    try:
        from wordcloud import WordCloud
        import matplotlib.pyplot as plt

        text = " ".join((fdf["Title"].fillna("") + " " + fdf["Summary (100 Words)"].fillna("")).tolist())
        wc = WordCloud(width=1000, height=380, background_color="white",
                       colormap="viridis", collocations=False).generate(text)
        fig, ax = plt.subplots(figsize=(10, 3.8))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig, use_container_width=True)
    except ImportError:
        st.warning("Word cloud needs the `wordcloud` package — run "
                   "`pip install wordcloud` and reload.", icon="⚠️")
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TAB 4 — AUTHORS & SOURCES
# ══════════════════════════════════════════════════════════════════════
with tab_authors:
    with st.container(border=True, key="authors_filters"):
        auth_pick = st.multiselect("Filter to specific authors", authors, default=[], key="auth_pick")

    fdf = df.copy()
    if auth_pick:
        fdf = fdf[fdf["Author"].apply(lambda a: any(x in a for x in auth_pick))]

    if fdf.empty:
        st.info("No articles match the current filters.")
        st.stop()

    src = source_distribution(fdf)
    show_sources = src["Source"].nunique() > 1

    if show_sources:
        c1, c2 = st.columns((3, 2))
    else:
        c1 = st.container()

    with c1:
        st.markdown('<div class="card"><h4>Top 10 authors</h4>', unsafe_allow_html=True)
        top_authors = explode_authors(fdf)["Author"].value_counts().head(10).reset_index()
        top_authors.columns = ["Author", "Articles"]
        fig = px.bar(top_authors.sort_values("Articles"), x="Articles", y="Author", orientation="h",
                     color_discrete_sequence=[ACCENT])
        st.plotly_chart(clean_chart(fig, h=380), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    if show_sources:
        with c2:
            st.markdown('<div class="card"><h4>Frequency of articles by source</h4>', unsafe_allow_html=True)
            src["% Share"] = (src["Articles"] / src["Articles"].sum() * 100).round(2)
            total_row = pd.DataFrame([{"Source": "Total", "Articles": src["Articles"].sum(),
                                        "% Share": 100.0}])
            st.dataframe(pd.concat([src, total_row], ignore_index=True), use_container_width=True,
                         hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="card"><h4>Article contributions by author</h4>', unsafe_allow_html=True)
    contrib = author_contribution_table(fdf, top_n=15)
    st.dataframe(contrib, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
