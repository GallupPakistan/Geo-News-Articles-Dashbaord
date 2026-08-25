"""Tests for compute_topics() and compute_sentiment() — the two functions
that were recently wrapped in @st.cache_data. These tests exist mainly to
guarantee the caching change didn't alter their output (st.cache_data
hashes function args and can silently return stale/wrong results if a
function is later changed to mutate its input in place)."""
import pandas as pd
import pytest

from common import compute_sentiment, compute_topics

vaderSentiment = pytest.importorskip("vaderSentiment", reason="optional dependency not installed")


def test_compute_topics_returns_none_topic_when_fewer_rows_than_clusters(sample_df):
    out, cluster_names = compute_topics(sample_df, n_clusters=10)
    assert cluster_names == {}
    assert out["Topic"].isna().all()


def test_compute_topics_does_not_mutate_the_input_dataframe(sample_df):
    original = sample_df.copy()
    compute_topics(sample_df, n_clusters=2)
    pd.testing.assert_frame_equal(sample_df, original)


def test_compute_sentiment_is_deterministic_across_repeated_calls(sample_df):
    first = compute_sentiment(sample_df)
    second = compute_sentiment(sample_df)
    pd.testing.assert_series_equal(first["Sentiment"], second["Sentiment"])


def test_compute_sentiment_scores_are_within_vader_bounds(sample_df):
    sdf = compute_sentiment(sample_df)
    assert sdf["Sentiment"].between(-1, 1).all()
