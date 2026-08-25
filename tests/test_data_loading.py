"""Integration test against the real bundled dataset (geo_news_data.csv).

Unlike the other test files, this one intentionally does NOT use the
synthetic sample_df fixture — its job is to catch cases where someone
edits geo_news_data.csv (or its column names) in a way that would break
every page of the app.
"""
from common import load_data


def test_bundled_csv_loads_with_expected_columns():
    df = load_data(None)
    for col in ["Title", "Author", "Publish Date", "Week", "Month"]:
        assert col in df.columns


def test_bundled_csv_has_no_unfilled_missing_authors():
    df = load_data(None)
    assert df["Author"].isna().sum() == 0


def test_bundled_csv_publish_dates_all_parse():
    df = load_data(None)
    # If the date format in the CSV ever drifts from "%d %B %Y", this
    # will start failing loudly instead of silently dropping rows from
    # every date-based chart.
    assert df["Publish Date"].isna().sum() == 0


def test_bundled_csv_is_not_empty():
    df = load_data(None)
    assert len(df) > 0
