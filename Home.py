import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import (
    avg_summary_words, busiest_day, coauthor_split, contributor_mix,
    inject_branding, kpi_card, kpi_grid, longest_streak,
    most_active_weekday, rolling_weekly_avg, sidebar_data_uploader,
    sidebar_filters, summary_word_counts, title_word_counts,
    week_over_week_counts, weekday_distribution,
)

inject_branding("Home")

df = sidebar_data_uploader()
fdf = sidebar_filters(df)

col_logo, col_title = st.columns((1, 6))
with col_logo:
    st.image("assets/geo_logo.png", width=80)
with col_title:
    st.title("📰 Opinions — Editorial Dashboard")
    st.caption("Overview of Geo News opinion articles: volume, authors, and reach over time")

st.divider()

if fdf.empty:
    st.info("No articles in the current filter.")
    st.stop()

# ── Headline KPIs: article volume, with week-over-week delta + sparkline ──
weekly_counts = fdf.groupby("Week").size()
this_week, last_week = week_over_week_counts(fdf)
span_days = (fdf["Publish Date"].max() - fdf["Publish Date"].min()).days if len(fdf) else 0

k1, k2, k3, k4 = st.columns(4)
kpi_card(k1, "📄 Articles", len(fdf),
         delta=f"{this_week - last_week:+d} this wk" if len(fdf) else None,
         spark=weekly_counts, key="spark_articles")
kpi_card(k2, "✍️ Authors", fdf["Author"].nunique(),
         spark=fdf.groupby("Week")["Author"].nunique(), color="#f7941e", key="spark_authors")
k3.metric("🗓️ Date span (days)", span_days)
k4.metric(
    "⚡ Articles / week (avg)",
    round(len(fdf) / max(span_days / 7, 1), 1) if span_days else 0,
)

st.divider()

# ── New KPIs — rendered as wrapping HTML tiles so nothing gets clipped ────
streak = longest_streak(fdf["Publish Date"])
b_day, b_day_count = busiest_day(fdf)
solo, co = coauthor_split(fdf)
avg_words = avg_summary_words(fdf)
top_weekday, top_weekday_count = most_active_weekday(fdf)
one_off, repeat = contributor_mix(fdf)

kpi_grid([
    {"emoji": "🔥", "label": "Longest streak", "value": f"{streak} day{'s' if streak != 1 else ''}",
     "sub": "Consecutive days with ≥1 article"},
    {"emoji": "📆", "label": "Busiest day", "value": f"{b_day_count} article{'s' if b_day_count != 1 else ''}",
     "sub": f"on {b_day:%d %b %Y}" if b_day else ""},
    {"emoji": "🤝", "label": "Solo vs co-authored", "value": f"{solo} / {co}",
     "sub": "Single-byline vs multi-byline"},
    {"emoji": "📝", "label": "Avg. summary length", "value": f"{avg_words:.0f} words"},
    {"emoji": "⭐", "label": "Most active weekday", "value": top_weekday or "—",
     "sub": f"{top_weekday_count} articles" if top_weekday else ""},
    {"emoji": "🔁", "label": "One-off vs repeat writers", "value": f"{one_off} / {repeat}",
     "sub": "Wrote once vs. wrote 2+ times"},
])

st.divider()
st.header("📊 Publishing volume")

c1, c2, c3 = st.columns((2, 1, 1))

with c1:
    st.subheader("📈 Publishing trend (weekly)")
    weekly = fdf.groupby("Week").size().reset_index(name="Articles")
    fig = px.area(weekly, x="Week", y="Articles", markers=True,
                   color_discrete_sequence=["#f7941e"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("🏆 Top 10 authors")
    top_authors = fdf["Author"].value_counts().head(10).reset_index()
    top_authors.columns = ["Author", "Articles"]
    fig = px.bar(top_authors.sort_values("Articles"), x="Articles", y="Author",
                 orientation="h", color_discrete_sequence=["#0c2f6b"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

with c3:
    st.subheader("🥯 Contributor mix")
    mix_df = pd.DataFrame({"Type": ["One-off writers", "Repeat writers"], "Count": [one_off, repeat]})
    fig = px.pie(mix_df, names="Type", values="Count", hole=0.55,
                 color_discrete_sequence=["#f7941e", "#0c2f6b"])
    fig.update_traces(textinfo="value+percent")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), showlegend=True,
                       legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("🌊 4-week rolling average")
roll = rolling_weekly_avg(fdf)
fig = px.line(roll, x="Week", y="Rolling avg", markers=True, color_discrete_sequence=["#0c2f6b"])
fig.add_bar(x=roll["Week"], y=roll["Articles"], marker_color="rgba(247,148,30,0.35)", name="Weekly")
fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                   paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.header("🧭 Publishing rhythm")

st.subheader("🗓️ Day-of-week pattern")
wd = weekday_distribution(fdf)
fig = px.bar(wd, x="Weekday", y="Articles", color_discrete_sequence=["#f7941e"])
fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                   paper_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.header("✏️ Editorial depth")

f1, f2 = st.columns(2)

with f1:
    st.subheader("🔡 Title length distribution")
    tw = title_word_counts(fdf)
    fig = px.histogram(tw, nbins=12, color_discrete_sequence=["#f7941e"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)", xaxis_title="Words in title",
                       yaxis_title="Articles", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with f2:
    st.subheader("📚 Summary length distribution")
    sw = summary_word_counts(fdf)
    fig = px.histogram(sw, nbins=12, color_discrete_sequence=["#0c2f6b"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)", xaxis_title="Words in summary",
                       yaxis_title="Articles", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Calendar heatmap — GitHub-style density grid ───────────────────────────
st.subheader("🔲 Calendar heatmap")
st.caption("Darker cells = more articles published that day")

cal = fdf.copy()
cal["Date"] = cal["Publish Date"].dt.date
daily = cal.groupby("Date").size()

full_range = pd.date_range(fdf["Publish Date"].min().normalize(),
                            fdf["Publish Date"].max().normalize(), freq="D")
daily = daily.reindex([d.date() for d in full_range], fill_value=0)
daily.index = pd.to_datetime(daily.index)

weekday_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
week_num = daily.index.isocalendar().week + (daily.index.isocalendar().year - daily.index.isocalendar().year.min()) * 53
weekday_lbl = daily.index.strftime("%a")

grid = (
    pd.DataFrame({"week": week_num, "weekday": weekday_lbl, "count": daily.values,
                  "date": daily.index.strftime("%d %b %Y")})
    .pivot(index="weekday", columns="week", values="count")
    .reindex(weekday_order)
)
hover = (
    pd.DataFrame({"week": week_num, "weekday": weekday_lbl, "date": daily.index.strftime("%d %b %Y")})
    .pivot(index="weekday", columns="week", values="date")
    .reindex(weekday_order)
)

vmax = max(int(np.nanmax(grid.values)), 1)
# Non-linear stops: most days sit at 1-2 articles, so a flat 0→vmax scale
# leaves them nearly indistinguishable from empty cells. Spread the low end
# out instead, and let color only approach the darkest navy near the true max.
stop_points = sorted(set([0, 1, min(2, vmax), max(vmax // 2, 2), vmax]))
stop_colors = ["#f4f6fb", "#cfe0f5", "#8fb3e0", "#4a76b8", "#0c2f6b"][:len(stop_points)]
colorscale = [[p / vmax, c] for p, c in zip(stop_points, stop_colors)]

fig = go.Figure(go.Heatmap(
    z=grid.values, x=grid.columns, y=grid.index, customdata=hover.values,
    colorscale=colorscale, zmin=0, zmax=vmax,
    hovertemplate="%{customdata}<br>%{z} article(s)<extra></extra>",
    showscale=False, xgap=3, ygap=3,
))
fig.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10),
                   plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                   xaxis=dict(showticklabels=False, title=None),
                   yaxis=dict(autorange="reversed"))
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.markdown(
    "👉 Use the pages in the sidebar for a closer look: **✍️ Authors**, **🏷️ Topics**, "
    "**📈 Trends**, **🌡️ Sentiment**, and the full **📄 Articles** table with search and export."
)