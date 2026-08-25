import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import (
    compute_sentiment, compute_topics, get_dataframe, inject_branding,
    kpi_grid, sentiment_by_author, sidebar_filters,
)

inject_branding("Sentiment")

df = get_dataframe()
fdf = sidebar_filters(df)

st.title("🌡️ Sentiment")
st.caption("Editorial tone pulse — VADER sentiment score run on each article's summary")

if fdf.empty:
    st.info("No articles in the current filter.")
    st.stop()

try:
    sdf = compute_sentiment(fdf)
except ImportError:
    st.warning(
        "Sentiment scoring needs the `vaderSentiment` package — run "
        "`pip install vaderSentiment` in this project's environment, then "
        "reload the page.",
        icon="⚠️",
    )
    st.stop()

avg_score = sdf["Sentiment"].mean()
pos_n = int((sdf["Sentiment"] > 0.05).sum())
neu_n = int(sdf["Sentiment"].between(-0.05, 0.05).sum())
neg_n = int((sdf["Sentiment"] < -0.05).sum())
most_pos_row = sdf.loc[sdf["Sentiment"].idxmax()]
most_neg_row = sdf.loc[sdf["Sentiment"].idxmin()]

kpi_grid([
    {"emoji": "🌡️", "label": "Average tone", "value": f"{avg_score:+.2f}",
     "sub": "-1 very negative · 0 neutral · +1 very positive"},
    {"emoji": "😊", "label": "Positive articles", "value": pos_n,
     "sub": f"{pos_n / len(sdf) * 100:.0f}% of the filtered set"},
    {"emoji": "😐", "label": "Neutral articles", "value": neu_n},
    {"emoji": "☹️", "label": "Negative articles", "value": neg_n},
    {"emoji": "🌟", "label": "Most positive piece", "value": most_pos_row["Title"][:40] + ("…" if len(most_pos_row["Title"]) > 40 else ""),
     "sub": f"score {most_pos_row['Sentiment']:+.2f}"},
    {"emoji": "⚡", "label": "Most negative piece", "value": most_neg_row["Title"][:40] + ("…" if len(most_neg_row["Title"]) > 40 else ""),
     "sub": f"score {most_neg_row['Sentiment']:+.2f}"},
])

st.divider()
st.header("🎚️ Overall tone")

c1, c2 = st.columns((1, 2))

with c1:
    st.subheader("Tone gauge")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_score,
        number={"valueformat": ".2f"},
        gauge={
            "axis": {"range": [-1, 1]},
            "bar": {"color": "#0c2f6b"},
            "steps": [
                {"range": [-1, -0.05], "color": "#f4a6a0"},
                {"range": [-0.05, 0.05], "color": "#e9ecf3"},
                {"range": [0.05, 1], "color": "#a8d5a0"},
            ],
        },
    ))
    fig.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("-1 = very negative · 0 = neutral · +1 = very positive")

with c2:
    st.subheader("Sentiment trend (weekly average)")
    weekly = sdf.groupby("Week")["Sentiment"].mean().reset_index()
    fig = px.line(weekly, x="Week", y="Sentiment", markers=True,
                  color_discrete_sequence=["#0c2f6b"])
    fig.add_hline(y=0, line_dash="dot", line_color="#999")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)", yaxis_range=[-1, 1])
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.header("📊 Distribution")

d1, d2, d3 = st.columns(3)

with d1:
    st.subheader("Score distribution")
    fig = px.histogram(sdf, x="Sentiment", nbins=20, color_discrete_sequence=["#f7941e"])
    fig.add_vline(x=0, line_dash="dot", line_color="#999")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with d2:
    st.subheader("Positive / neutral / negative")
    tone_df = pd.DataFrame({"Tone": ["Positive", "Neutral", "Negative"], "Articles": [pos_n, neu_n, neg_n]})
    fig = px.pie(tone_df, names="Tone", values="Articles", hole=0.5,
                 color="Tone", color_discrete_map={"Positive": "#a8d5a0", "Neutral": "#c7cedd", "Negative": "#f4a6a0"})
    fig.update_traces(textinfo="value+percent")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, use_container_width=True)

with d3:
    st.subheader("Sentiment by weekday")
    wk = sdf.groupby(sdf["Publish Date"].dt.day_name())["Sentiment"].mean()
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    wk = wk.reindex(order, fill_value=0).reset_index()
    wk.columns = ["Weekday", "Avg sentiment"]
    fig = px.bar(wk, x="Weekday", y="Avg sentiment",
                 color="Avg sentiment", color_continuous_scale=["#f4a6a0", "#e9ecf3", "#a8d5a0"])
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.header("🧭 Sentiment over time & by writer")

e1, e2 = st.columns(2)

with e1:
    st.subheader("Monthly average sentiment")
    monthly = sdf.groupby("Month")["Sentiment"].mean().reset_index()
    fig = px.bar(monthly, x="Month", y="Sentiment",
                 color="Sentiment", color_continuous_scale=["#f4a6a0", "#e9ecf3", "#a8d5a0"])
    fig.add_hline(y=0, line_dash="dot", line_color="#999")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False, yaxis_range=[-1, 1])
    st.plotly_chart(fig, use_container_width=True)

with e2:
    st.subheader("Sentiment by author (top 10)")
    sba = sentiment_by_author(sdf)
    if not sba.empty:
        fig = px.bar(sba, x="Avg sentiment", y="Author", orientation="h",
                     color="Avg sentiment", color_continuous_scale=["#f4a6a0", "#e9ecf3", "#a8d5a0"])
        fig.add_vline(x=0, line_dash="dot", line_color="#999")
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

st.subheader("🏷️ Sentiment by topic")
n_clusters = st.slider("Number of topic clusters", 3, 10, 6, key="sentiment_clusters")
tdf, cluster_names = compute_topics(sdf, n_clusters)
if cluster_names:
    tdf["Sentiment"] = sdf["Sentiment"].values
    by_topic = tdf.groupby("Topic")["Sentiment"].mean().reset_index().sort_values("Sentiment")
    fig = px.bar(by_topic, x="Sentiment", y="Topic", orientation="h",
                 color="Sentiment", color_continuous_scale=["#f4a6a0", "#e9ecf3", "#a8d5a0"])
    fig.add_vline(x=0, line_dash="dot", line_color="#999")
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                       paper_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False,
                       height=max(300, 32 * len(by_topic)))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough articles in the current filter to build topic clusters.")

st.subheader("📝 Sentiment vs. summary length")
sdf["Summary words"] = sdf["Summary (100 Words)"].fillna("").str.split().apply(len)
fig = px.scatter(sdf, x="Summary words", y="Sentiment", color="Sentiment",
                  color_continuous_scale=["#f4a6a0", "#e9ecf3", "#a8d5a0"],
                  hover_data={"Title": True, "Sentiment": ":.2f"})
fig.add_hline(y=0, line_dash="dot", line_color="#999")
fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)",
                   paper_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False)
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.header("🔝 Most positive & most negative articles")
p1, p2 = st.columns(2)
top_pos = sdf.sort_values("Sentiment", ascending=False).head(5)
top_neg = sdf.sort_values("Sentiment").head(5)

with p1:
    st.markdown("**😊 Most positive**")
    st.dataframe(
        top_pos[["Publish Date", "Title", "Author", "Sentiment"]]
        .assign(**{"Publish Date": top_pos["Publish Date"].dt.strftime("%d %b %Y"),
                   "Sentiment": top_pos["Sentiment"].round(2)}),
        use_container_width=True, height=220, hide_index=True,
    )

with p2:
    st.markdown("**☹️ Most negative**")
    st.dataframe(
        top_neg[["Publish Date", "Title", "Author", "Sentiment"]]
        .assign(**{"Publish Date": top_neg["Publish Date"].dt.strftime("%d %b %Y"),
                   "Sentiment": top_neg["Sentiment"].round(2)}),
        use_container_width=True, height=220, hide_index=True,
    )
