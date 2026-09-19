"""Common markdown formatting helpers for per-datatype rendering."""


def literal_via_fence(content):
    return "\n{}\n".format("\n".join(f"    {line}" for line in content.splitlines()))


def indicate_data_truncated():
    return "\n**Warning:** The above data has been truncated to be embedded in this document.\n\n"


def pre_formatted_contents(markdown):
    return f"<pre>{markdown}</pre>"
