from galaxy.util import topsort


def test_topsort_level_stability():
    data = [
        (0, 2),
        (1, 2),
        (2, 3),
        (2, 4),
        (3, 4),
        (3, 5),
        (6, 2),
    ]
    assert topsort.topsort_levels(data)[0] == [0, 1, 6]
    assert topsort.topsort(data) == [0, 1, 6, 2, 3, 4, 5]
    # Swap first two edges - so 1 appears first
    swap(data, 0, 1)
    assert topsort.topsort_levels(data)[0] == [1, 0, 6]
    assert topsort.topsort(data) == [1, 0, 6, 2, 3, 4, 5]

    # Shouldn't really affect sorting of 1 0 6
    swap(data, 3, 4)
    assert topsort.topsort_levels(data)[0] == [1, 0, 6]
    assert topsort.topsort(data) == [1, 0, 6, 2, 3, 4, 5]

    # Place 0 before 6 in original list
    swap(data, 1, 6)
    assert topsort.topsort_levels(data)[0] == [1, 6, 0]
    assert topsort.topsort(data) == [1, 6, 0, 2, 3, 4, 5]


def test_topsort_doc():
    assert topsort.topsort([(1, 2), (3, 3)]) == [1, 3, 2]


def swap(lst, i, j):
    tmp = lst[j]
    lst[j] = lst[i]
    lst[i] = tmp
