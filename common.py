"""Shared data loading + branding helpers used by every page."""

import base64
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

if sys.version_info < (3, 9):
    raise RuntimeError(
        f"This dashboard needs Python 3.9 or newer — you're running "
        f"{sys.version_info.major}.{sys.version_info.minor}. "
        f"Install a newer Python (e.g. from python.org) and re-run "
        f"`pip install -r requirements.txt` with it."
    )

ROOT = Path(__file__).parent
DATA_PATH = ROOT / "Final_Geo_News_.xlsx"
LOGO_PATH = ROOT / "assets" / "geo_logo.png"
BANNER_PATH = ROOT / "assets" / "opinions_banner.png"


@st.cache_data
def load_data(file=None):
    if file is None:
        df = pd.read_excel(DATA_PATH)
    elif str(file.name).endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    df["Publish Date"] = pd.to_datetime(df["Publish Date"], format="%d %B %Y", errors="coerce")
    df["Author"] = df["Author"].fillna("Unattributed / Staff")
    df["Week"] = df["Publish Date"].dt.to_period("W").apply(lambda p: p.start_time)
    df["Month"] = df["Publish Date"].dt.to_period("M").astype(str)
    return df


@st.cache_data
def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def inject_branding(page_title: str):
    """Sets page config, paints the banner image behind the header, and
    drops the Geo News logo into the sidebar. Call once at the top of every page."""
    st.set_page_config(page_title=f"Geo News — {page_title}", page_icon="📰", layout="wide")

    banner_b64 = _b64(BANNER_PATH)
    style_css = (
        '<style>'
        '[data-testid="stAppViewContainer"] > .main {'
        'background-image: linear-gradient(rgba(255,255,255,0.93), rgba(255,255,255,0.93)), '
        f'url("data:image/png;base64,{banner_b64}");'
        'background-size: contain; background-repeat: no-repeat; '
        'background-position: top center; background-attachment: fixed;'
        '}'
        '[data-testid="stHeader"] { background: rgba(0,0,0,0); }'
        '[data-testid="stToolbar"] { visibility: hidden; }'
        'section[data-testid="stSidebar"] { background-color: #0b1f4d; }'
        'section[data-testid="stSidebar"] * { color: #f5f7fa !important; }'
        'div[data-testid="stMetric"] { background: rgba(255,255,255,0.85); border-radius: 10px; '
        'padding: 10px 14px; border: 1px solid #e3e7ee; }'
        '</style>'
    )
    st.markdown(style_css, unsafe_allow_html=True)

    with st.sidebar:
        st.image(str(LOGO_PATH), width=90)
        st.markdown("### Geo News — Opinions")
        st.caption("Editorial analytics dashboard")
        st.divider()


def sidebar_data_uploader():
    """Loads the default dataset into session_state (no uploader UI shown
    in the sidebar). Kept for backward compatibility with Home.py's call."""
    if "df" not in st.session_state:
        st.session_state["df"] = load_data(None)
    return st.session_state["df"]


def get_dataframe():
    """Used by every page other than Home — reads whatever is currently
    loaded in session_state (default dataset, or the user's uploaded one)."""
    if "df" not in st.session_state:
        st.session_state["df"] = load_data(None)
    return st.session_state["df"]


def sidebar_filters(df: pd.DataFrame):
    st.sidebar.header("Filters")

    min_date, max_date = df["Publish Date"].min(), df["Publish Date"].max()
    date_range = st.sidebar.date_input(
        "Publish date range", value=(min_date.date(), max_date.date()),
        min_value=min_date.date(), max_value=max_date.date(),
    )

    authors = sorted(df["Author"].unique())
    selected_authors = st.sidebar.multiselect("Author", authors, default=[])

    search_term = st.sidebar.text_input("Search title / summary")

    mask = (
        (df["Publish Date"].dt.date >= date_range[0])
        & (df["Publish Date"].dt.date <= date_range[-1])
    )
    if selected_authors:
        mask &= df["Author"].isin(selected_authors)
    if search_term:
        term = search_term.lower()
        mask &= (
            df["Title"].str.lower().str.contains(term, na=False)
            | df["Summary (100 Words)"].str.lower().str.contains(term, na=False)
        )
    return df[mask].copy()


# ── KPI cards: sparklines + week-over-week deltas ──────────────────────────

def _hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def sparkline_fig(series: pd.Series, color: str = "#0c2f6b") -> go.Figure:
    """Tiny axis-free area chart meant to sit underneath an st.metric card."""
    fig = go.Figure(
        go.Scatter(
            x=list(range(len(series))), y=series.values, mode="lines",
            line=dict(color=color, width=2), fill="tozeroy",
            fillcolor=_hex_to_rgba(color, 0.15),
        )
    )
    fig.update_layout(
        height=44, margin=dict(l=0, r=0, t=2, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def kpi_card(col, label: str, value, delta=None, spark: pd.Series = None,
             color: str = "#0c2f6b", key: str = None):
    """An st.metric plus an optional sparkline underneath, in one column."""
    with col:
        col.metric(label, value, delta=delta)
        if spark is not None and len(spark) > 1:
            st.plotly_chart(
                sparkline_fig(spark, color), use_container_width=True,
                config={"displayModeBar": False},
                key=key or f"spark_{label}",
            )


# ── KPI grid v2: HTML cards that wrap instead of truncating ────────────────
# st.metric() clips long labels/values when many columns are packed into one
# row (see the cramped "7 arti…" / "100 w…" cards). These render as flexible
# HTML tiles instead — text wraps to a second line rather than being cut off,
# and the grid re-flows on narrow / mobile screens.

def kpi_grid(cards: list, min_width: int = 200):
    """cards: list of dicts with keys:
        emoji (str), label (str), value (str), delta (str, optional),
        delta_positive (bool, optional, default True), sub (str, optional)
    Renders as a responsive CSS grid — no st.columns, so nothing truncates.
    """
    tiles = []
    for c in cards:
        delta_html = ""
        if c.get("delta"):
            up = c.get("delta_positive", True)
            dcolor = "#1a7f37" if up else "#c0392b"
            tri = "▲" if up else "▼"
            delta_html = (
                f'<div style="font-size:0.78rem;color:{dcolor};font-weight:700;'
                f'margin-top:4px;">{tri} {c["delta"]}</div>'
            )
        sub_html = (
            f'<div style="font-size:0.72rem;color:#6b7280;margin-top:2px;">{c["sub"]}</div>'
            if c.get("sub") else ""
        )
        tiles.append(
            '<div style="background:rgba(255,255,255,0.94);border:1px solid #e3e7ee;'
            'border-radius:14px;padding:14px 16px 12px;min-height:96px;'
            'box-shadow:0 1px 2px rgba(12,47,107,0.06);">'
            '<div style="font-size:0.8rem;color:#4b5573;font-weight:600;line-height:1.3;'
            'white-space:normal;overflow-wrap:anywhere;">'
            f'<span style="font-size:1.05rem;">{c.get("emoji", "")}</span> {c["label"]}'
            '</div>'
            '<div style="font-size:1.6rem;font-weight:800;color:#0c2f6b;margin-top:5px;'
            f'line-height:1.15;white-space:normal;overflow-wrap:anywhere;">{c["value"]}</div>'
            f'{delta_html}{sub_html}'
            '</div>'
        )

    grid_html = (
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax({min_width}px,1fr));'
        f'gap:12px;margin:6px 0 4px;">{"".join(tiles)}</div>'
    )
    st.markdown(grid_html, unsafe_allow_html=True)


def week_over_week_counts(fdf: pd.DataFrame):
    """Article counts for the last 7 days of the filtered range vs. the 7
    days before that — powers the 'this week vs last week' delta arrows."""
    max_date = fdf["Publish Date"].max()
    if pd.isna(max_date):
        return 0, 0
    this_week = fdf[fdf["Publish Date"] > max_date - pd.Timedelta(days=7)]
    last_week = fdf[
        (fdf["Publish Date"] <= max_date - pd.Timedelta(days=7))
        & (fdf["Publish Date"] > max_date - pd.Timedelta(days=14))
    ]
    return len(this_week), len(last_week)


# ── New KPI calculations ────────────────────────────────────────────────────

def longest_streak(dates: pd.Series) -> int:
    """Longest run of consecutive calendar days with >= 1 article."""
    days = sorted(set(pd.to_datetime(dates).dropna().dt.date))
    if not days:
        return 0
    longest = streak = 1
    for i in range(1, len(days)):
        if (days[i] - days[i - 1]).days == 1:
            streak += 1
        else:
            streak = 1
        longest = max(longest, streak)
    return longest


def busiest_day(fdf: pd.DataFrame):
    """(date, count) for the single busiest publishing day."""
    if fdf.empty:
        return None, 0
    counts = fdf["Publish Date"].dt.date.value_counts()
    return counts.idxmax(), int(counts.max())


def busiest_week(fdf: pd.DataFrame):
    """(week_start, count) for the single busiest publishing week."""
    if fdf.empty:
        return None, 0
    counts = fdf.groupby("Week").size()
    return counts.idxmax(), int(counts.max())


def is_coauthored(author_series: pd.Series) -> pd.Series:
    return author_series.str.contains(",", na=False)


def coauthor_split(fdf: pd.DataFrame):
    """(solo_count, co_authored_count)."""
    co = is_coauthored(fdf["Author"])
    return int((~co).sum()), int(co.sum())


def avg_summary_words(fdf: pd.DataFrame, col: str = "Summary (100 Words)") -> float:
    if fdf.empty:
        return 0.0
    return float(fdf[col].fillna("").str.split().apply(len).mean())


def most_active_weekday(fdf: pd.DataFrame):
    """(weekday_name, count) for the weekday with the most articles."""
    if fdf.empty:
        return None, 0
    counts = fdf["Publish Date"].dt.day_name().value_counts()
    return counts.idxmax(), int(counts.max())


def weekday_distribution(fdf: pd.DataFrame) -> pd.DataFrame:
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    counts = fdf["Publish Date"].dt.day_name().value_counts().reindex(order, fill_value=0)
    return pd.DataFrame({"Weekday": counts.index, "Articles": counts.values})


def explode_authors(fdf: pd.DataFrame) -> pd.DataFrame:
    """One row per (article, author) — splits comma-separated bylines."""
    exploded = fdf.copy()
    exploded["Author"] = exploded["Author"].str.split(r",\s*")
    return exploded.explode("Author").reset_index(drop=True)


def contributor_mix(fdf: pd.DataFrame):
    """(one_off_count, repeat_count) — authors (after exploding bylines) who
    appear exactly once in the filtered set vs. those who appear more than once."""
    counts = explode_authors(fdf)["Author"].value_counts()
    return int((counts == 1).sum()), int((counts > 1).sum())


def coauthor_pairs(fdf: pd.DataFrame) -> pd.DataFrame:
    """One row per unique pair of authors who co-wrote an article together,
    with a 'Articles' count — the edge list for a collaboration network."""
    co = fdf[is_coauthored(fdf["Author"])]
    rows = []
    for authors in co["Author"].str.split(r",\s*"):
        for i in range(len(authors)):
            for j in range(i + 1, len(authors)):
                pair = tuple(sorted((authors[i], authors[j])))
                rows.append(pair)
    if not rows:
        return pd.DataFrame(columns=["Author A", "Author B", "Articles"])
    pair_counts = pd.Series(rows).value_counts().reset_index()
    pair_counts.columns = ["pair", "Articles"]
    pair_counts["Author A"] = pair_counts["pair"].apply(lambda p: p[0])
    pair_counts["Author B"] = pair_counts["pair"].apply(lambda p: p[1])
    return pair_counts[["Author A", "Author B", "Articles"]]


# ── Extra time-series / distribution helpers (power the added charts) ─────

def monthly_counts(fdf: pd.DataFrame) -> pd.DataFrame:
    counts = fdf.groupby("Month").size().reset_index(name="Articles")
    return counts.sort_values("Month")


def cumulative_counts(fdf: pd.DataFrame) -> pd.DataFrame:
    daily = fdf.groupby(fdf["Publish Date"].dt.date).size().sort_index()
    out = daily.cumsum().reset_index()
    out.columns = ["Date", "Cumulative articles"]
    return out


def rolling_weekly_avg(fdf: pd.DataFrame, window: int = 4) -> pd.DataFrame:
    weekly = fdf.groupby("Week").size().reset_index(name="Articles").sort_values("Week")
    weekly["Rolling avg"] = weekly["Articles"].rolling(window, min_periods=1).mean()
    return weekly


def publishing_gaps(fdf: pd.DataFrame) -> pd.Series:
    """Days between each article and the previous one (article-level, not day-level)."""
    dates = fdf["Publish Date"].dropna().sort_values()
    return dates.diff().dt.days.dropna()


def language_distribution(fdf: pd.DataFrame) -> pd.DataFrame:
    counts = fdf["Language"].value_counts().reset_index()
    counts.columns = ["Language", "Articles"]
    return counts


def source_distribution(fdf: pd.DataFrame) -> pd.DataFrame:
    counts = fdf["Source"].value_counts().reset_index()
    counts.columns = ["Source", "Articles"]
    return counts


def title_word_counts(fdf: pd.DataFrame) -> pd.Series:
    return fdf["Title"].fillna("").str.split().apply(len)


def summary_word_counts(fdf: pd.DataFrame, col: str = "Summary (100 Words)") -> pd.Series:
    return fdf[col].fillna("").str.split().apply(len)


def author_month_heatmap(fdf: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    exploded = explode_authors(fdf)
    top_authors = exploded["Author"].value_counts().head(top_n).index
    sub = exploded[exploded["Author"].isin(top_authors)]
    pivot = pd.crosstab(sub["Author"], sub["Month"]).reindex(top_authors)
    months = sorted(fdf["Month"].dropna().unique())
    return pivot.reindex(columns=months, fill_value=0)


def new_vs_returning_authors(fdf: pd.DataFrame) -> pd.DataFrame:
    """Per week: how many bylines belong to an author writing for the first
    time in the filtered set vs. one who has written before."""
    exploded = explode_authors(fdf).sort_values("Publish Date")
    seen = set()
    rows = []
    for _, r in exploded.iterrows():
        rows.append({"Week": r["Week"], "Status": "Returning" if r["Author"] in seen else "New"})
        seen.add(r["Author"])
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=["Week", "Status", "Bylines"])
    return out.groupby(["Week", "Status"]).size().reset_index(name="Bylines")


def top_authors_cumulative_share(fdf: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Weekly cumulative share of articles: top-N authors vs. everyone else."""
    exploded = explode_authors(fdf)
    top_authors = set(exploded["Author"].value_counts().head(top_n).index)
    tagged = exploded.copy()
    tagged["Group"] = tagged["Author"].apply(lambda a: "Top contributors" if a in top_authors else "Everyone else")
    weekly = tagged.groupby(["Week", "Group"]).size().unstack(fill_value=0).sort_index().cumsum()
    weekly_pct = weekly.div(weekly.sum(axis=1), axis=0) * 100
    out = weekly_pct.reset_index().melt(id_vars="Week", var_name="Group", value_name="Share (%)")
    return out


def sentiment_by_author(sdf: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    exploded = explode_authors(sdf)
    top_authors = exploded["Author"].value_counts().head(top_n).index
    sub = exploded[exploded["Author"].isin(top_authors)]
    out = sub.groupby("Author")["Sentiment"].mean().reindex(top_authors).reset_index()
    out.columns = ["Author", "Avg sentiment"]
    return out.sort_values("Avg sentiment")


def solo_co_by_author(fdf: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    """For each of the top-N authors: how many of their bylines were solo
    pieces vs. co-authored ones."""
    top_authors = fdf["Author"].value_counts().head(top_n).index
    sub = fdf[fdf["Author"].isin(top_authors)].copy()
    sub["Type"] = is_coauthored(sub["Author"]).map({True: "Co-authored", False: "Solo"})
    out = sub.groupby(["Author", "Type"]).size().reset_index(name="Articles")
    return out


def avg_words_by_author(fdf: pd.DataFrame, top_n: int = 12,
                         col: str = "Summary (100 Words)") -> pd.DataFrame:
    exploded = explode_authors(fdf)
    top_authors = exploded["Author"].value_counts().head(top_n).index
    sub = exploded[exploded["Author"].isin(top_authors)].copy()
    sub["Words"] = sub[col].fillna("").str.split().apply(len)
    out = sub.groupby("Author")["Words"].mean().reindex(top_authors).reset_index()
    out.columns = ["Author", "Avg words"]
    return out.sort_values("Avg words")


def author_gap_stats(fdf: pd.DataFrame, top_n: int = 8) -> pd.DataFrame:
    """Days between consecutive articles, per author (top-N most prolific) —
    powers a box plot of publishing consistency."""
    exploded = explode_authors(fdf).sort_values("Publish Date")
    top_authors = exploded["Author"].value_counts().head(top_n).index
    rows = []
    for a in top_authors:
        dates = exploded[exploded["Author"] == a]["Publish Date"].dropna().sort_values()
        gaps = dates.diff().dt.days.dropna()
        for g in gaps:
            rows.append({"Author": a, "Gap (days)": g})
    return pd.DataFrame(rows)


def weekday_topic_heatmap(tdf: pd.DataFrame) -> pd.DataFrame:
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday = tdf["Publish Date"].dt.day_name()
    pivot = pd.crosstab(weekday, tdf["Topic"]).reindex(order, fill_value=0)
    return pivot


# ── Topic clustering (shared by the Topics and Trends pages) ───────────────

CUSTOM_STOP = {
    "pakistan", "pakistan's", "said", "will", "new", "says", "year", "years",
    "country", "world", "one", "also", "us", "u.s", "govt", "government",
}


@st.cache_data(show_spinner="Clustering topics…")
def compute_topics(fdf: pd.DataFrame, n_clusters: int, summary_col: str = "Summary (100 Words)"):
    """Runs TF-IDF + KMeans over title+summary text and returns a copy of
    fdf with a 'Topic' column, plus the {cluster_id: label} name map.
    Returns (fdf, {}) unchanged if there isn't enough data to cluster."""
    if len(fdf) < n_clusters:
        out = fdf.copy()
        out["Topic"] = None
        return out, {}

    text = fdf["Title"].fillna("") + " " + fdf[summary_col].fillna("")
    vec = TfidfVectorizer(stop_words="english", max_features=2000, ngram_range=(1, 2), min_df=2)
    X = vec.fit_transform(text)
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(X)

    out = fdf.copy()
    out["Topic Cluster"] = labels

    terms = vec.get_feature_names_out()
    cluster_names = {}
    for i in range(n_clusters):
        center = km.cluster_centers_[i]
        top_idx = center.argsort()[-3:][::-1]
        cluster_names[i] = ", ".join(terms[j] for j in top_idx)

    out["Topic"] = out["Topic Cluster"].map(cluster_names)
    return out, cluster_names


def topic_momentum(tdf: pd.DataFrame) -> pd.DataFrame:
    """Compares each topic's article count in the most recent full week of
    data vs. the week before — powers 'rising / falling theme' indicators.
    Requires tdf to already have a 'Topic' column from compute_topics."""
    if tdf.empty or "Topic" not in tdf.columns or tdf["Topic"].isna().all():
        return pd.DataFrame(columns=["Topic", "This week", "Last week", "Change"])

    weeks = sorted(tdf["Week"].dropna().unique())
    if len(weeks) < 2:
        latest, prior = (weeks[-1], None) if weeks else (None, None)
    else:
        latest, prior = weeks[-1], weeks[-2]

    this_week = tdf[tdf["Week"] == latest]["Topic"].value_counts()
    last_week = tdf[tdf["Week"] == prior]["Topic"].value_counts() if prior is not None else pd.Series(dtype=int)

    all_topics = tdf["Topic"].dropna().unique()
    out = pd.DataFrame({
        "Topic": all_topics,
        "This week": [int(this_week.get(t, 0)) for t in all_topics],
        "Last week": [int(last_week.get(t, 0)) for t in all_topics],
    })
    out["Change"] = out["This week"] - out["Last week"]
    return out.sort_values("Change", ascending=False).reset_index(drop=True)


def day_of_month_distribution(fdf: pd.DataFrame) -> pd.DataFrame:
    counts = fdf["Publish Date"].dt.day.value_counts().reindex(range(1, 32), fill_value=0)
    return pd.DataFrame({"Day of month": counts.index, "Articles": counts.values})


def week_over_week_pct(fdf: pd.DataFrame) -> pd.DataFrame:
    weekly = fdf.groupby("Week").size().reset_index(name="Articles").sort_values("Week")
    weekly["Change (%)"] = weekly["Articles"].pct_change().mul(100).round(1)
    return weekly.dropna(subset=["Change (%)"])


def topic_month_heatmap(tdf: pd.DataFrame) -> pd.DataFrame:
    if tdf.empty or "Topic" not in tdf.columns or tdf["Topic"].isna().all():
        return pd.DataFrame()
    return pd.crosstab(tdf["Topic"], tdf["Month"])


def topic_stats(tdf: pd.DataFrame) -> pd.DataFrame:
    """Per topic: article count, avg title word count, unique author count."""
    if tdf.empty or "Topic" not in tdf.columns or tdf["Topic"].isna().all():
        return pd.DataFrame(columns=["Topic", "Articles", "Avg title words", "Unique authors"])
    work = tdf.dropna(subset=["Topic"]).copy()
    work["Title words"] = work["Title"].fillna("").str.split().apply(len)
    exploded = explode_authors(work)
    out = work.groupby("Topic").agg(
        Articles=("Title", "count"),
        **{"Avg title words": ("Title words", "mean")},
    ).reset_index()
    authors_per_topic = exploded.groupby("Topic")["Author"].nunique().reset_index(name="Unique authors")
    return out.merge(authors_per_topic, on="Topic", how="left").sort_values("Articles", ascending=False)


# ── Classification engine (rule-based) ──────────────────────────────────
# Turns free-text Title + Summary into a single "Category" per article,
# and lets us pull out short "themes" (frequent phrases) within a category.
# There's no ground-truth label in the source data, so this is a
# transparent keyword scorer rather than a black-box model: every category
# is just a list of trigger words/phrases, the article's text is scored
# against each list (title hits count double), and the highest-scoring
# category wins. Ties fall back to the order below. Articles that don't
# hit any keyword land in "Society & Culture".

CATEGORY_KEYWORDS = {
    "Economy": [
        "tax", "economy", "economic", "gdp", "inflation", "budget", "financ",
        "psx", "stock exchange", "credit rating", "moody's", "petrol price",
        "diesel", "fuel price", "revenue", "imf", "debt", "fiscal", "rupee",
        "currency", "trade deficit", "exports", "imports", "sovereign",
        "growth", "unemployment", "subsidy", "pump",
    ],
    "Politics": [
        "pml-n", "ppp", "pti", "election", "politic", "democracy", "party",
        "assembly", "parliament", "polls", "rigging", "imran khan", "nawaz",
        "prime minister", "cabinet", "opposition", "vote",
    ],
    "Governance": [
        "governance", "devolution", "province", "institution", "reform",
        "bureaucracy", "administration", "civil service", "local government",
        "centre", "system", "competence",
    ],
    "Foreign Relations": [
        "diplomat", "diplomacy", "foreign relation", "ceasefire", "bilateral",
        "ambassador", "foreign minister", "geopolitic", "soft power",
        "sco", "united nations", " mou", "summit", "negotiation",
        "peace deal", "trump", "washington", "beijing", "mediation",
        "regional peace",
    ],
    "Climate & Environment": [
        "climate", "flood", "monsoon", "river", "water", "hydro",
        "indus water", " iwt", "drought", "glacier", "environment",
        "heatwave", "pollution", "irrigation", "rain",
    ],
    "Security & Conflict": [
        "terror", "security", "militant", "strike", "war", "army",
        "military", "iran", "israel", "gaza", "field marshal", "munir",
        "crossfire", "conflict",
    ],
    "Crime & Justice": [
        "murder", "cctv", "crime", "abuse", "justice", "court", "police",
        "legal case", "investigation",
    ],
    "Human Rights & Society": [
        "human rights", " rights", "population", "demographic", "child",
        "displaced", "registry", "gender", "welfare", "social",
    ],
    "Health": [
        "health", "diet", "disease", "medical", "hospital", "nutrition",
    ],
    "Sports": [
        "fifa", "football", "cricket", "test against", " odi", "series",
        "tournament", "idol crowned", "psl",
    ],
    "Science & Technology": [
        "artificial intelligence", " ai ", " ai-", "digital", "tech",
        "fibre", "internet", "machines", "cybersecurity", " data ",
    ],
    "Culture & Entertainment": [
        "shah rukh khan", "entertainment", "film", "music", "culture",
        "idol", "cinema", "art ",
    ],
}

DEFAULT_CATEGORY = "Society & Culture"
CATEGORY_ORDER = list(CATEGORY_KEYWORDS.keys()) + [DEFAULT_CATEGORY]


def _score_text(title: str, body: str) -> str:
    title_l, body_l = f" {title.lower()} ", f" {body.lower()} "
    best_cat, best_score = DEFAULT_CATEGORY, 0
    for cat, kws in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in kws:
            score += 2 * title_l.count(kw.lower()) + body_l.count(kw.lower())
        if score > best_score:
            best_cat, best_score = cat, score
    return best_cat


@st.cache_data
def classify_articles(fdf: pd.DataFrame, summary_col: str = "Summary (100 Words)") -> pd.DataFrame:
    """Adds a 'Category' column (rule-based, see CATEGORY_KEYWORDS above)."""
    out = fdf.copy()
    out["Category"] = [
        _score_text(str(t), str(s))
        for t, s in zip(out["Title"].fillna(""), out[summary_col].fillna(""))
    ]
    return out


def category_distribution(cdf: pd.DataFrame) -> pd.DataFrame:
    counts = cdf["Category"].value_counts().reset_index()
    counts.columns = ["Category", "Articles"]
    counts["Share (%)"] = (counts["Articles"] / counts["Articles"].sum() * 100).round(1)
    return counts


def category_month_trend(cdf: pd.DataFrame, top_n: int = 6) -> pd.DataFrame:
    """Monthly share (%) of articles for the top-N categories — the data
    behind the multi-line 'Classification Trend' chart."""
    if cdf.empty:
        return pd.DataFrame(columns=["Month", "Category", "Share (%)"])
    top_cats = cdf["Category"].value_counts().head(top_n).index.tolist()
    monthly_total = cdf.groupby("Month").size()
    sub = cdf[cdf["Category"].isin(top_cats)]
    pivot = sub.groupby(["Month", "Category"]).size().reset_index(name="Articles")
    pivot["Share (%)"] = pivot.apply(
        lambda r: round(100 * r["Articles"] / monthly_total.get(r["Month"], 1), 1), axis=1
    )
    months = sorted(cdf["Month"].dropna().unique())
    full = pd.MultiIndex.from_product([months, top_cats], names=["Month", "Category"]).to_frame(index=False)
    out = full.merge(pivot, on=["Month", "Category"], how="left").fillna({"Articles": 0, "Share (%)": 0})
    return out.sort_values(["Category", "Month"])


def category_author_diversity(cdf: pd.DataFrame) -> pd.DataFrame:
    """Per category: how many distinct authors have written in it, and how
    many articles — a 'is this category one voice or many?' view."""
    exploded = explode_authors(cdf)
    out = exploded.groupby("Category").agg(
        Articles=("Title", "count"),
        **{"Unique authors": ("Author", "nunique")},
    ).reset_index()
    out["Articles per author"] = (out["Articles"] / out["Unique authors"]).round(1)
    return out.sort_values("Articles", ascending=False)


THEME_STOP = CUSTOM_STOP | {"pakistan's", "it's", "don't", "isn't"}


def category_themes(cdf: pd.DataFrame, category: str, top_n: int = 8) -> pd.DataFrame:
    """Top recurring 2-word phrases within one category's articles — the
    'Themes Covered in <Category>' bars. Falls back to single words when
    there isn't enough text to support repeated bigrams."""
    from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS

    sub = cdf[cdf["Category"] == category]
    corpus = (sub["Title"].fillna("") + " " + sub["Summary (100 Words)"].fillna("")).tolist()
    corpus = [c for c in corpus if c.strip()]
    if not corpus:
        return pd.DataFrame(columns=["Theme", "Share (%)"])

    stop = list(ENGLISH_STOP_WORDS.union(THEME_STOP))
    for ngram in [(2, 2), (1, 1)]:
        vec = CountVectorizer(ngram_range=ngram, stop_words=stop, min_df=1, max_features=300)
        try:
            X = vec.fit_transform(corpus)
        except ValueError:
            continue
        sums = np.asarray(X.sum(axis=0)).ravel()
        terms = vec.get_feature_names_out()
        pairs = sorted(zip(terms, sums), key=lambda p: -p[1])
        pairs = [(t, c) for t, c in pairs if c > (1 if ngram == (1, 1) else 0)][:top_n]
        if pairs:
            total = max(sum(c for _, c in pairs), 1)
            out = pd.DataFrame(pairs, columns=["Theme", "Count"])
            out["Theme"] = out["Theme"].str.title()
            out["Share (%)"] = (out["Count"] / total * 100).round(0)
            return out[["Theme", "Share (%)"]]
    return pd.DataFrame(columns=["Theme", "Share (%)"])


def author_contribution_table(cdf: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Per top-N author: their single most-written category + article count
    — powers the 'Article Contributions by Author' table."""
    exploded = explode_authors(cdf)
    top_authors = exploded["Author"].value_counts().head(top_n).index.tolist()
    rows = []
    for a in top_authors:
        sub = exploded[exploded["Author"] == a]
        top_cat = sub["Category"].value_counts().idxmax() if "Category" in sub else "—"
        rows.append({"Author": a, "Top category": top_cat, "Articles": len(sub)})
    out = pd.DataFrame(rows).sort_values("Articles", ascending=False)
    return out


# ── Sentiment (VADER — same tool used in the ARIA project) ─────────────────

@st.cache_resource
def get_sentiment_analyzer():
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    return SentimentIntensityAnalyzer()


@st.cache_data(show_spinner="Scoring sentiment…")
def compute_sentiment(fdf: pd.DataFrame, col: str = "Summary (100 Words)") -> pd.DataFrame:
    """Adds a 'Sentiment' column (-1..+1 VADER compound score) to a copy of fdf."""
    analyzer = get_sentiment_analyzer()
    out = fdf.copy()
    out["Sentiment"] = out[col].fillna("").apply(
        lambda t: analyzer.polarity_scores(str(t))["compound"]
    )
    return out
