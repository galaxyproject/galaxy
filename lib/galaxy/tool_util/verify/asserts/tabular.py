import re


def get_first_line(output, comment):
    """
    get the first non-comment and non-empty line
    """
    if comment != "":
        match = re.search(f"^([^{comment}].*)$", output, flags=re.MULTILINE)
    else:
        match = re.search("^(.+)$", output, flags=re.MULTILINE)
    if match is None:
        return None
    else:
        return match.group(1)


def assert_has_n_columns(output, n, sep='\t', comment=""):
    """ Asserts the tabular output contains n columns. The optional
    sep argument specifies the column seperator used to determine the
    number of columns. The optional comment argument specifies
    comment characters"""
    n = int(n)
    first_line = get_first_line(output, comment)
    assert first_line is not None, "Was expecting output with %d columns, but output was empty" % n
    n_columns = len(first_line.split(sep))
    assert n_columns == n, f"Expected {n} columns in output, found {n_columns} columns"
