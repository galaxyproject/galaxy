"""Jinja2-based rendering of workflow_state tree reports.

Single ``Environment`` shared by every CLI's ``--report-markdown`` path.
Templates live in ``templates/reports/`` and consume report data exclusively
through ``model_dump(by_alias=True, mode="json")`` — no Python methods, no
custom filters or globals — so they render identically under Nunjucks in
the TypeScript mirror. See JINJA_REPORTS_PLAN.md.
"""

from collections.abc import Callable
from datetime import (
    datetime,
    timezone,
)
from typing import (
    Any,
)

REPORT_VERSION = "26.1"

from jinja2 import (
    Environment,
    PackageLoader,
    select_autoescape,
)
from pydantic import BaseModel

_ENV: Environment | None = None


def _get_env() -> Environment:
    """Build (once) the shared Jinja2 environment.

    Deliberately minimal — no custom filters or globals — because every
    feature used here must also exist in Nunjucks for the TS mirror.
    """
    global _ENV
    if _ENV is None:
        _ENV = Environment(
            loader=PackageLoader("galaxy.tool_util.workflow_state", "templates/reports"),
            autoescape=select_autoescape(enabled_extensions=()),  # markdown, not HTML
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=False,
        )
    return _ENV


def _default_meta() -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "report_version": REPORT_VERSION,
    }


def render_report(
    template_name: str,
    report: BaseModel,
    meta: dict[str, Any] | None = None,
) -> str:
    """Render ``report`` through ``template_name``.

    The template receives two top-level variables:

    - ``report`` — ``report.model_dump(by_alias=True, mode="json")``
    - ``meta``   — rendering metadata (``generated_at``, ``report_version``)
    """
    template = _get_env().get_template(template_name)
    context = {
        "report": report.model_dump(by_alias=True, mode="json"),
        "meta": meta if meta is not None else _default_meta(),
    }
    return template.render(**context)


def make_markdown_renderer(template_name: str) -> Callable[[BaseModel], str]:
    """Return a ``Callable[[BaseModel], str]`` bound to ``template_name``.

    Matches the signature ``emit_reports``/``run_tree`` already expect for
    ``markdown_formatter``, so swapping from a hand-written
    ``format_*_markdown`` to a template is a one-line change at each CLI.
    """

    def _render(report: BaseModel) -> str:
        return render_report(template_name, report)

    return _render
