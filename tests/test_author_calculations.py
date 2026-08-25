from common import (
    coauthor_pairs, coauthor_split, contributor_mix, explode_authors,
    is_coauthored,
)


def test_is_coauthored_flags_only_comma_separated_bylines(sample_df):
    flags = is_coauthored(sample_df["Author"]).tolist()
    # rows: Aisha | Bilal,Sana | Aisha | Zara | Zara
    assert flags == [False, True, False, False, False]


def test_coauthor_split_counts_solo_vs_co_authored_rows(sample_df):
    solo, co = coauthor_split(sample_df)
    assert solo == 4  # every row except the Bilal/Sana one
    assert co == 1


def test_explode_authors_splits_comma_separated_bylines_into_two_rows(sample_df):
    exploded = explode_authors(sample_df)
    # 5 original rows, one of which has 2 authors -> 6 exploded rows
    assert len(exploded) == 6
    assert set(exploded["Author"]) == {"Aisha Khan", "Bilal Ahmed", "Sana Malik", "Zara Iqbal"}


def test_contributor_mix_separates_one_off_from_repeat_authors(sample_df):
    one_off, repeat = contributor_mix(sample_df)
    # Aisha Khan (x2) and Zara Iqbal (x2) are repeats; Bilal Ahmed and
    # Sana Malik (x1 each, from the co-authored piece) are one-off.
    assert one_off == 2
    assert repeat == 2


def test_coauthor_pairs_returns_one_row_for_the_only_pair(sample_df):
    pairs = coauthor_pairs(sample_df)
    assert len(pairs) == 1
    row = pairs.iloc[0]
    assert {row["Author A"], row["Author B"]} == {"Bilal Ahmed", "Sana Malik"}
    assert row["Articles"] == 1


def test_coauthor_pairs_empty_when_no_co_authored_articles(sample_df):
    solo_only = sample_df[~is_coauthored(sample_df["Author"])]
    pairs = coauthor_pairs(solo_only)
    assert pairs.empty
    assert list(pairs.columns) == ["Author A", "Author B", "Articles"]
