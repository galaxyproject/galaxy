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
