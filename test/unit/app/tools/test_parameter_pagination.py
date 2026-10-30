from galaxy.tools.parameters.pagination import accumulate_with_filter


def _query(rows):
    def query_fn(*, offset, limit):
        return rows[offset : offset + limit], len(rows)

    return query_fn


def test_accumulate_pages_single_matches():
    query_fn = _query(list(range(5)))
    assert accumulate_with_filter(query_fn, lambda row: row + 1, 0, 2) == ([1, 2], 5, True)
    assert accumulate_with_filter(query_fn, lambda row: row + 1, 2, 2) == ([3, 4], 5, True)
    assert accumulate_with_filter(query_fn, lambda row: row + 1, 4, 2) == ([5], 5, False)


def test_accumulate_skips_filtered_rows():
    query_fn = _query(list(range(6)))
    matches, total, has_more = accumulate_with_filter(query_fn, lambda row: row if row % 2 else None, 1, 5)
    assert (matches, total, has_more) == ([3, 5], 6, False)


def _page_with_two_entries_for_a(rows, offset, limit):
    def filter_fn(row):
        return [(row, "direct"), (row, "map over")] if row == "a" else (row, "direct")

    return accumulate_with_filter(_query(rows), filter_fn, offset, limit)


def test_accumulate_finishes_a_multi_match_row():
    page = [("b", "direct"), ("a", "direct"), ("a", "map over")]
    assert _page_with_two_entries_for_a(["b", "a"], 0, 2) == (page, 2, False)
    assert _page_with_two_entries_for_a(["b", "a", "c"], 0, 2) == (page, 3, True)
    # an offset landing mid-row resumes with the row's remaining entries
    assert _page_with_two_entries_for_a(["b", "a", "c"], 2, 1) == ([("a", "map over")], 3, True)
