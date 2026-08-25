"""Shared pytest fixtures.

`sample_df` is a small, hand-built dataset (not the real CSV) so every
expected value in the tests can be verified by hand and won't drift if
geo_news_data.csv is ever edited. Layout (5 rows):

    Date        Weekday     Author(s)                 Summary words
    2026-06-01  Monday      Aisha Khan                4
    2026-06-02  Tuesday     Bilal Ahmed, Sana Malik    2   (co-authored)
    2026-06-03  Wednesday   Aisha Khan                3
    2026-06-03  Wednesday   Zara Iqbal                1   (2nd article same day)
    2026-06-10  Wednesday   Zara Iqbal                5

This gives:
  - a 3-day publishing streak (Jun 1-3) then a gap to Jun 10
  - a busiest day (Jun 3, 2 articles) that's unambiguous
  - a busiest/most-active weekday (Wednesday, 3 articles across 2 dates)
  - one co-authored byline -> explodes into 2 author rows
  - repeat authors (Aisha x2, Zara x2) vs. one-off authors (Bilal, Sana)
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def sample_df() -> pd.DataFrame:
    rows = [
        ("2026-06-01", "Aisha Khan",               "One Two Three",    "one two three four"),
        ("2026-06-02", "Bilal Ahmed, Sana Malik",   "Co Written Piece", "one two"),
        ("2026-06-03", "Aisha Khan",                "Another One",      "one two three"),
        ("2026-06-03", "Zara Iqbal",                "Same Day Piece",   "one"),
        ("2026-06-10", "Zara Iqbal",                "Later One",        "one two three four five"),
    ]
    df = pd.DataFrame(rows, columns=["Publish Date", "Author", "Title", "Summary (100 Words)"])
    df["Publish Date"] = pd.to_datetime(df["Publish Date"])
    df["Week"] = df["Publish Date"].dt.to_period("W").apply(lambda p: p.start_time)
    df["Month"] = df["Publish Date"].dt.to_period("M").astype(str)
    return df


@pytest.fixture
def empty_df(sample_df) -> pd.DataFrame:
    return sample_df.iloc[0:0].copy()
