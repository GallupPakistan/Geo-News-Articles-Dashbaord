import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import (
    compute_topics, cumulative_counts, day_of_month_distribution,
    get_dataframe, inject_branding, kpi_grid, monthly_counts,
    publishing_gaps, rolling_weekly_avg, sidebar_filters, topic_momentum,
    topic_month_heatmap, weekday_distribution,
    week_over_week_pct,
)

inject_branding("Trends")

df = get_dataframe()
fdf = sidebar_filters(df)

st.title("📈 Trends")
st.caption("Publishing rhythm — which days get the most opinion pieces, and how themes rise and fall")

if fdf.empty:
    st.info("No articles in the current filter.")
    st.stop()

weekly = fdf.groupby("Week").size()
roll = rolling_weekly_avg(fdf)
gaps = publishing_gaps(fdf)
wow = week_over_week_pct(fdf)

kpi_grid([
    {"emoji": "📅", "label": "Weeks of coverage", "value": fdf["Week"].nunique()},
    {"emoji": "📈", "label": "Peak week volume", "value": int(weekly.max()) if len(weekly) else 0,
     "sub": f"week of {weekly.idxmax():%d %b %Y}" if len(weekly) else ""},
    {"emoji": "🌊", "label": "Current 4-wk avg", "value": f"{roll['Rolling avg'].iloc[-1]:.1f}" if len(roll) else "—"},
    {"emoji": "⏳", "label": "Median gap", "value": f"{gaps.median():.0f} day(s)" if len(gaps) else "—",
     "sub": "Between consecutive articles"},
    {"emoji": "📊", "label": "Latest week vs. prior", "value": f"{wow['Change (%)'].iloc[-1]:+.0f}%" if len(wow) else "—",
     "delta_positive": bool(wow['Change (%)'].iloc[-1] >= 0) if len(wow) else True,
     "delta": "week-over-week" if len(wow) else None},
])

st.divider()
st.header("🗓️ Publishing rhythm")

r1, r2 = st.columns(2)

with r1:
    st.subheader("Day-of-week distribution")
    wd = weekday_distribution(fdf)
    fig = px.bar(wd, x="Weekday", y="Articles", color_discrete_sequence=["#0c2f6b"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

with r2:
    st.subheader("Day-of-month distribution")
    dom = day_of_month_distribution(fdf)
    dom = dom[dom["Articles"] > 0] if dom["Articles"].sum() else dom
    fig = px.bar(dom, x="Day of month", y="Articles", color_discrete_sequence=["#f7941e"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.header("📉 Volume over time")

v1, v2, v3 = st.columns(3)

with v1:
    st.subheader("Monthly volume")
    monthly = monthly_counts(fdf)
    fig = px.bar(monthly, x="Month", y="Articles", color_discrete_sequence=["#0c2f6b"], text="Articles")
    fig.update_traces(textposition="outside")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

with v2:
    st.subheader("Cumulative growth")
    cum = cumulative_counts(fdf)
    fig = px.line(cum, x="Date", y="Cumulative articles", color_discrete_sequence=["#f7941e"])
    fig.update_traces(fill="tozeroy", fillcolor="rgba(247,148,30,0.15)")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

with v3:
    st.subheader("Week-over-week % change")
    if not wow.empty:
        colors = ["#1a7f37" if v >= 0 else "#c0392b" for v in wow["Change (%)"]]
        fig = go.Figure(go.Bar(x=wow["Week"], y=wow["Change (%)"], marker_color=colors))
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", yaxis_title="Change vs. prior week (%)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Need at least two weeks of data.")

st.subheader("⏳ Gap between articles")
if len(gaps):
    fig = px.histogram(gaps, nbins=min(15, gaps.nunique() or 1), color_discrete_sequence=["#0c2f6b"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)", xaxis_title="Days since previous article",
                       yaxis_title="Count", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough articles to compute gaps.")

st.divider()
st.header("🧵 Topic trends")

n_clusters = st.slider("Number of topic clusters", 3, 10, 6, key="trends_clusters")
tdf, cluster_names = compute_topics(fdf, n_clusters)

if cluster_names:
    st.subheader("Topic trend over time")
    st.caption("Weekly volume per auto-grouped theme — watch clusters rise and fade")
    weekly_topic = tdf.groupby(["Week", "Topic"]).size().reset_index(name="Articles")
    fig = px.area(
        weekly_topic, x="Week", y="Articles", color="Topic",
        color_discrete_sequence=px.colors.qualitative.Set2,
        groupnorm=None,
    )
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🌡️ Topic × month seasonality")
    tm = topic_month_heatmap(tdf)
    fig = go.Figure(go.Heatmap(
        z=tm.values, x=tm.columns, y=tm.index,
        colorscale=[[0, "#eef1f7"], [1, "#0c2f6b"]],
        hovertemplate="%{y}<br>%{x}<br>%{z} article(s)<extra></extra>",
    ))
    fig.update_layout(height=max(300, 28 * len(tm)), margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("🚀 Topic momentum")
    st.caption("Latest week vs. the week before — which themes are heating up or cooling off")
    momentum = topic_momentum(tdf)

    if momentum.empty:
        st.info("Not enough weeks of data to compare momentum yet.")
    else:
        fig = go.Figure(go.Bar(
            x=momentum["Change"], y=momentum["Topic"], orientation="h",
            marker_color=["#1a7f37" if v >= 0 else "#c0392b" for v in momentum["Change"]],
        ))
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", xaxis_title="Change in articles vs. prior week",
                           height=max(300, 32 * len(momentum)))
        st.plotly_chart(fig, use_container_width=True)

        cols = st.columns(min(4, len(momentum)))
        for i, row in momentum.iterrows():
            col = cols[i % len(cols)]
            arrow = "▲" if row["Change"] > 0 else ("▼" if row["Change"] < 0 else "→")
            col.metric(row["Topic"], f"{row['This week']} article(s)",
                       f"{arrow} {row['Change']:+d} vs. last wk")
else:
    st.info("Not enough articles in the current filter to build topic clusters.")
