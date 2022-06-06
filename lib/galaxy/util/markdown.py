class MarkdownFormatHelpers:
    """Common markdown formatting helpers for per-datatype rendering."""

    @staticmethod
    def literal_via_fence(content):
        return "\n%s\n" % "\n".join(f"    {line}" for line in content.splitlines())

    @staticmethod
    def indicate_data_truncated():
        return "\n**Warning:** The above data has been truncated to be embedded in this document.\n\n"

    @staticmethod
    def pre_formatted_contents(markdown):
        return f"<pre>{markdown}</pre>"
