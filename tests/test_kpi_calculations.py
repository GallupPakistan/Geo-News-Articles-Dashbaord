import pandas as pd

from common import (
    avg_summary_words, busiest_day, busiest_week, longest_streak,
    most_active_weekday, publishing_gaps, week_over_week_counts,
)


def test_longest_streak_finds_the_three_day_run(sample_df):
    # Jun 1, 2, 3 are consecutive; Jun 10 is isolated -> longest run is 3.
    assert longest_streak(sample_df["Publish Date"]) == 3


def test_longest_streak_empty_series_is_zero(empty_df):
    assert longest_streak(empty_df["Publish Date"]) == 0


def test_longest_streak_ignores_nat_values():
    dates = pd.to_datetime(["2026-06-01", None, "2026-06-02"])
    assert longest_streak(pd.Series(dates)) == 2


def test_busiest_day_picks_the_unambiguous_two_article_day(sample_df):
    day, count = busiest_day(sample_df)
    assert day == pd.Timestamp("2026-06-03").date()
    assert count == 2


def test_busiest_day_on_empty_df_returns_none_and_zero(empty_df):
    assert busiest_day(empty_df) == (None, 0)


def test_busiest_week_matches_the_week_containing_busiest_day(sample_df):
    week, count = busiest_week(sample_df)
    assert count == 4  # Jun 1, 2, 3, 3 all fall in the same ISO week
    assert week == sample_df["Week"].iloc[0]


def test_most_active_weekday_is_wednesday(sample_df):
    weekday, count = most_active_weekday(sample_df)
    assert weekday == "Wednesday"
    assert count == 3


def test_most_active_weekday_on_empty_df(empty_df):
    assert most_active_weekday(empty_df) == (None, 0)


def test_avg_summary_words_matches_hand_count(sample_df):
    # word counts per row: 4, 2, 3, 1, 5 -> mean 3.0
    assert avg_summary_words(sample_df) == 3.0


def test_avg_summary_words_on_empty_df_is_zero(empty_df):
    assert avg_summary_words(empty_df) == 0.0


def test_publishing_gaps_returns_days_between_consecutive_articles(sample_df):
    gaps = publishing_gaps(sample_df).tolist()
    # sorted dates: 06-01, 06-02, 06-03, 06-03, 06-10
    # -> gaps: 1, 1, 0, 7
    assert gaps == [1.0, 1.0, 0.0, 7.0]


def test_week_over_week_counts_on_empty_df(empty_df):
    assert week_over_week_counts(empty_df) == (0, 0)
