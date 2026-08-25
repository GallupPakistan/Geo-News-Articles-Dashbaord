import pandas as pd
import plotly.express as px
import streamlit as st

from common import get_dataframe, inject_branding, kpi_grid

inject_branding("About")

st.title("ℹ️ About this dashboard")
st.caption("How this Geo News — Opinions dashboard was built, and the process behind it")

st.markdown(
    "This dashboard follows a standard KPI-dashboard build process — from picking the "
    "right metrics through to shipping something the editorial team will actually use."
)

# ── Live dataset snapshot — pulled straight from the currently loaded CSV ──
df = get_dataframe()
n_articles = len(df)
n_authors = df["Author"].nunique()
n_sources = df["Source"].nunique()
n_languages = df["Language"].nunique()
missing_authors = int(df["Author"].eq("Unattributed / Staff").sum())
date_min = df["Publish Date"].min()
date_max = df["Publish Date"].max()
if pd.notna(date_min) and pd.notna(date_max):
    date_range_str = f'{date_min:%d %b %Y} – {date_max:%d %b %Y}'
else:
    date_range_str = "n/a"

st.divider()
st.header("📦 Live dataset snapshot")
st.caption("Computed from the CSV currently loaded into this dashboard — updates automatically if you upload a new file on the Home page.")

kpi_grid([
    {"emoji": "📰", "label": "Articles loaded", "value": n_articles},
    {"emoji": "✍️", "label": "Unique authors", "value": n_authors},
    {"emoji": "🏷️", "label": "Sources", "value": n_sources},
    {"emoji": "🌐", "label": "Languages", "value": n_languages},
    {"emoji": "🕳️", "label": "Missing author (filled)", "value": missing_authors,
     "sub": f"{missing_authors / max(n_articles, 1):.0%} of articles"},
    {"emoji": "📅", "label": "Date range", "value": date_range_str},
])

month_counts = df.dropna(subset=["Publish Date"]).copy()
month_counts["Month"] = month_counts["Publish Date"].dt.to_period("M").astype(str)
month_counts = month_counts.groupby("Month").size().reset_index(name="Articles")

top_authors = df["Author"].value_counts().head(10).reset_index()
top_authors.columns = ["Author", "Articles"]

c1, c2 = st.columns(2)
with c1:
    fig_month = px.bar(month_counts, x="Month", y="Articles",
                        color_discrete_sequence=["#0c2f6b"], title="Articles per month")
    fig_month.update_layout(margin=dict(l=10, r=10, t=40, b=10), plot_bgcolor="rgba(0,0,0,0)",
                             paper_bgcolor="rgba(0,0,0,0)", height=320)
    st.plotly_chart(fig_month, use_container_width=True)
with c2:
    fig_top = px.bar(top_authors.sort_values("Articles"), x="Articles", y="Author", orientation="h",
                      color_discrete_sequence=["#f7941e"], title="Top 10 authors")
    fig_top.update_layout(margin=dict(l=10, r=10, t=40, b=10), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", height=320)
    st.plotly_chart(fig_top, use_container_width=True)

st.divider()

# ── Data quality panel ──────────────────────────────────────────────────
st.header("🔍 Data quality panel")
st.caption("An honest audit of the currently loaded CSV — missing values, duplicates, and parsing issues.")

dup_titles = int(df["Title"].duplicated().sum())
dup_urls = int(df["Article URL"].duplicated().sum())
summary_lens = df["Summary (100 Words)"].dropna().str.split().str.len()
unparsed_dates = int(df["Publish Date"].isna().sum())

kpi_grid([
    {"emoji": "🕳️", "label": "Missing author", "value": missing_authors,
     "sub": f"{missing_authors / max(n_articles, 1):.0%} of articles"},
    {"emoji": "📄", "label": "Duplicate titles", "value": dup_titles},
    {"emoji": "🔗", "label": "Duplicate URLs", "value": dup_urls},
    {"emoji": "📏", "label": "Shortest summary", "value": f"{int(summary_lens.min()) if len(summary_lens) else 0} words"},
    {"emoji": "📐", "label": "Longest summary", "value": f"{int(summary_lens.max()) if len(summary_lens) else 0} words"},
    {"emoji": "⚠️", "label": "Unparseable dates", "value": unparsed_dates},
])

st.divider()

# ── Publishing cadence ──────────────────────────────────────────────────
st.header("🗓️ Publishing cadence")
st.caption("How often the desk actually publishes, computed from Publish Date.")

dated = df.dropna(subset=["Publish Date"]).sort_values("Publish Date")
if len(dated) > 1:
    span_days = (dated["Publish Date"].max() - dated["Publish Date"].min()).days
    weeks_spanned = max(span_days / 7, 1)
    avg_per_week = len(dated) / weeks_spanned
    gaps = dated["Publish Date"].diff().dropna().dt.days
    longest_gap = int(gaps.max()) if len(gaps) else 0
    busiest_day = dated["Publish Date"].dt.date.value_counts()
    busiest_day_date, busiest_day_count = busiest_day.index[0], int(busiest_day.iloc[0])
    weekday_count = int((dated["Publish Date"].dt.dayofweek < 5).sum())
    weekend_count = int((dated["Publish Date"].dt.dayofweek >= 5).sum())
else:
    avg_per_week, longest_gap = 0, 0
    busiest_day_date, busiest_day_count = "n/a", 0
    weekday_count, weekend_count = 0, 0

kpi_grid([
    {"emoji": "📈", "label": "Avg. articles / week", "value": f"{avg_per_week:.1f}"},
    {"emoji": "⏳", "label": "Longest gap", "value": f"{longest_gap} day(s)"},
    {"emoji": "🔥", "label": "Busiest day", "value": str(busiest_day_date),
     "sub": f"{busiest_day_count} article(s)"},
    {"emoji": "🗓️", "label": "Weekday vs weekend", "value": f"{weekday_count} / {weekend_count}"},
])

st.divider()

# ── Author roster summary ───────────────────────────────────────────────
st.header("✍️ Author roster summary")
st.caption("A compact view of the contributor base.")

author_counts = df["Author"].value_counts()
one_off = int((author_counts == 1).sum())
repeat = int((author_counts > 1).sum())
avg_articles_per_author = n_articles / max(n_authors, 1)
most_recent_row = df.dropna(subset=["Publish Date"]).sort_values("Publish Date").iloc[-1] if len(dated) else None
most_recent_author = most_recent_row["Author"] if most_recent_row is not None else "n/a"

kpi_grid([
    {"emoji": "1️⃣", "label": "One-off contributors", "value": one_off},
    {"emoji": "🔁", "label": "Repeat authors", "value": repeat},
    {"emoji": "📊", "label": "Avg. articles / author", "value": f"{avg_articles_per_author:.1f}"},
    {"emoji": "🆕", "label": "Most recent byline", "value": most_recent_author},
])

st.divider()

# ── Content stats from summaries ────────────────────────────────────────
st.header("📝 Content stats")
st.caption("Lightweight text stats from the Summary (100 Words) column.")

total_words = int(summary_lens.sum()) if len(summary_lens) else 0
avg_words = summary_lens.mean() if len(summary_lens) else 0
longest_idx = summary_lens.idxmax() if len(summary_lens) else None
shortest_idx = summary_lens.idxmin() if len(summary_lens) else None
longest_title = df.loc[longest_idx, "Title"] if longest_idx is not None else "n/a"
shortest_title = df.loc[shortest_idx, "Title"] if shortest_idx is not None else "n/a"

kpi_grid([
    {"emoji": "🔢", "label": "Total summary words", "value": f"{total_words:,}"},
    {"emoji": "📊", "label": "Avg. words / summary", "value": f"{avg_words:.0f}"},
    {"emoji": "📏", "label": "Longest summary", "value": longest_title},
    {"emoji": "✂️", "label": "Shortest summary", "value": shortest_title},
])

st.divider()

# ── Dataset file info ───────────────────────────────────────────────────
st.header("🗂️ Dataset file info")
st.caption("Metadata about the currently loaded file.")

col_info = pd.DataFrame({
    "Column": df.columns,
    "Type": [str(df[c].dtype) for c in df.columns],
    "Non-null": [int(df[c].notna().sum()) for c in df.columns],
})

kpi_grid([
    {"emoji": "📋", "label": "Rows", "value": len(df)},
    {"emoji": "📑", "label": "Columns", "value": len(df.columns)},
])
st.dataframe(col_info, use_container_width=True, hide_index=True)

st.divider()

st.header("🛠️ How this dashboard was built")
st.markdown(
    f"- Started with what editors actually care about — article volume, author output, "
    f"publishing rhythm, topic mix, and tone — rather than vanity metrics.\n"
    f"- Multi-page Streamlit layout (Home → Authors → Topics → Trends → Sentiment → "
    f"Articles → About) so each question has its own focused view.\n"
    f"- Built on Streamlit + Plotly for fast iteration and native support for interactive "
    f"charts, filters, and CSV export.\n"
    f"- Data is validated and typed on load — dates parsed, {missing_authors} missing "
    f"author field(s) filled as 'Unattributed / Staff', week/month columns derived — "
    f"via the shared `load_data()` helper.\n"
    f"- Currently loaded: **{n_articles} articles** from **{n_sources} source(s)** across "
    f"**{n_languages} language(s)**, spanning **{date_range_str}**.\n"
    f"- Sidebar filters (date range, author, search) and a CSV replace/upload option on the "
    f"Home page make the dashboard reusable as new data comes in."
)