from ..lint import SkipLint

try:
    from lxml import etree
except ImportError:
    etree = None


def lint_via_xsd(tool_xml, lint_ctx):
    if not lint_ctx.use_schema:
        raise SkipLint()
    if etree is None:
        lint_ctx.error("Requested linting via XML Schema but lxml is unavailable")
        return
