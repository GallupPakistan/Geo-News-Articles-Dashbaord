import plotly.express as px
import streamlit as st

from common import (
    coauthor_split, cumulative_counts, get_dataframe, inject_branding,
    kpi_grid, monthly_counts, publishing_gaps, rolling_weekly_avg,
    sidebar_filters, summary_word_counts, title_word_counts,
    weekday_distribution,
)

inject_branding("Articles")

df = get_dataframe()
fdf = sidebar_filters(df)

st.title("📄 Articles")
st.caption("Full list — filter from the sidebar, search, and export")

if fdf.empty:
    st.info("No articles in the current filter.")
    st.stop()

solo, co = coauthor_split(fdf)
sw = summary_word_counts(fdf)
tw = title_word_counts(fdf)

kpi_grid([
    {"emoji": "📄", "label": "Articles in view", "value": len(fdf)},
    {"emoji": "✍️", "label": "Unique authors", "value": fdf["Author"].nunique()},
    {"emoji": "🤝", "label": "Solo vs co-authored", "value": f"{solo} / {co}"},
    {"emoji": "📝", "label": "Avg. summary words", "value": f"{sw.mean():.0f}"},
    {"emoji": "🔡", "label": "Avg. title words", "value": f"{tw.mean():.1f}"},
    {"emoji": "🗓️", "label": "Date range", "value": f"{fdf['Publish Date'].min():%d %b} → {fdf['Publish Date'].max():%d %b}"},
])

st.divider()
st.header("📊 Quick stats for this view")

a1, a2, a3 = st.columns(3)

with a1:
    st.subheader("📅 Articles per month")
    monthly = monthly_counts(fdf)
    fig = px.bar(monthly, x="Month", y="Articles", color_discrete_sequence=["#0c2f6b"], text="Articles")
    fig.update_traces(textposition="outside")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

with a2:
    st.subheader("🗓️ Day-of-week pattern")
    wd = weekday_distribution(fdf)
    fig = px.bar(wd, x="Weekday", y="Articles", color_discrete_sequence=["#f7941e"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

with a3:
    st.subheader("🏆 Top 5 authors")
    top5 = fdf["Author"].value_counts().head(5).reset_index()
    top5.columns = ["Author", "Articles"]
    fig = px.bar(top5.sort_values("Articles"), x="Articles", y="Author", orientation="h",
                 color_discrete_sequence=["#0c2f6b"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

a4, a5, a6 = st.columns(3)

with a4:
    st.subheader("📈 Cumulative articles")
    cum = cumulative_counts(fdf)
    fig = px.line(cum, x="Date", y="Cumulative articles", color_discrete_sequence=["#f7941e"])
    fig.update_traces(fill="tozeroy", fillcolor="rgba(247,148,30,0.15)")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

with a5:
    st.subheader("🌊 4-week rolling average")
    roll = rolling_weekly_avg(fdf)
    fig = px.line(roll, x="Week", y="Rolling avg", markers=True, color_discrete_sequence=["#0c2f6b"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

with a6:
    st.subheader("⏳ Gap between articles")
    gaps = publishing_gaps(fdf)
    if len(gaps):
        fig = px.histogram(gaps, nbins=min(15, gaps.nunique() or 1), color_discrete_sequence=["#f7941e"])
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", xaxis_title="Days since previous",
                           showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough articles to compute gaps.")

a7, a8 = st.columns(2)

with a7:
    st.subheader("🔡 Title length distribution")
    fig = px.histogram(tw, nbins=12, color_discrete_sequence=["#0c2f6b"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)", xaxis_title="Words in title", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with a8:
    st.subheader("📚 Summary length distribution")
    fig = px.histogram(sw, nbins=12, color_discrete_sequence=["#f7941e"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)", xaxis_title="Words in summary", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.header(f"📋 {len(fdf)} article(s)")

display_cols = ["Publish Date", "Title", "Author", "Summary (100 Words)", "Article URL"]
show_df = fdf[display_cols].sort_values("Publish Date", ascending=False).reset_index(drop=True)
show_df["Publish Date"] = show_df["Publish Date"].dt.strftime("%d %b %Y")

st.dataframe(
    show_df,
    use_container_width=True,
    height=550,
    column_config={
        "Article URL": st.column_config.LinkColumn("Article URL"),
        "Summary (100 Words)": st.column_config.TextColumn("Summary", width="large"),
    },
)

csv = show_df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download filtered data as CSV", csv, "geo_news_filtered.csv", "text/csv")
