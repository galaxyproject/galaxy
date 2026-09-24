#!/usr/bin/env python
"""Generate Galaxy Markdown directive artifacts from directives.yml.

directives.yml is the source of truth for the Galaxy Markdown directive registry.
This script renders/generates everything downstream of it:

  * client/src/components/Markdown/directives.md     - human-readable reference
  * client/src/components/Markdown/Utilities/requirements.yml - directive -> required object
  * lib/galaxy/managers/_markdown_directives.py      - validator registry consumed by markdown_parse

The generated Python module keeps ``galaxy.managers.markdown_parse`` self-contained (no
YAML/file dependency at import) so it remains reusable outside Galaxy (e.g. gxformat2).

Usage::

    python scripts/markdown_directives_doc.py            # (re)write generated artifacts
    python scripts/markdown_directives_doc.py --check     # verify, non-zero exit on drift
"""

import argparse
import os
import re
import sys
import unicodedata

import yaml

MARKDOWN_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "client", "src", "components", "Markdown")
)
LIB_MANAGERS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib", "galaxy", "managers"))
DIRECTIVES_YML = os.path.join(MARKDOWN_DIR, "directives.yml")
REQUIREMENTS_YML = os.path.join(MARKDOWN_DIR, "Utilities", "requirements.yml")
OUTPUT_MD = os.path.join(MARKDOWN_DIR, "directives.md")
GENERATED_PY = os.path.join(LIB_MANAGERS_DIR, "_markdown_directives.py")
MARKDOWN_UTIL_PY = os.path.join(LIB_MANAGERS_DIR, "markdown_util.py")

CATEGORY_ORDER = ["dataset", "collection", "invocation", "workflow", "job", "visualization", "utility"]
CATEGORY_TITLES = {
    "dataset": "Dataset directives",
    "collection": "Collection directives",
    "invocation": "Invocation directives",
    "workflow": "Workflow directives",
    "job": "Job directives",
    "visualization": "Visualization directive",
    "utility": "Utility & instance directives",
}

TYPE_ORDER = ["label", "id", "int", "boolean", "enum", "string", "path"]
TYPE_NOTES = {
    "label": "Workflow input/output/step label; resolved to an ID per invocation.",
    "id": "Encoded (export) or numeric (internal) object ID.",
    "int": "Integer.",
    "boolean": "`true` or `false`.",
    "enum": "One of a fixed set of values.",
    "string": "Free display text.",
    "path": "File within a composite / extra-files dataset.",
}

CONTEXT_ORDER = ["report", "page", "notebook", "invocation"]
CONTEXT_NOTES = {
    "report": "Workflow report template — labels resolve per invocation.",
    "page": "Page / direct contexts — encoded or numeric IDs.",
    "notebook": "History-relative reference (notebooks).",
    "invocation": "Invocation reference — usually injected automatically.",
}


def load_directives(path=DIRECTIVES_YML):
    """Return (shared_arguments, parameter_sets, directives) parsed from directives.yml."""
    with open(path) as f:
        data = yaml.safe_load(f)
    shared_arguments = data.get("_shared_arguments", [])
    parameter_sets = data.get("_parameter_sets", {})
    directives = {key: value for key, value in data.items() if not key.startswith("_")}
    return shared_arguments, parameter_sets, directives


def resolve_parameters(entry, parameter_sets):
    """Merge a directive's shared parameter_set and inline parameters, preserving order."""
    parameters = {}
    set_name = entry.get("parameter_set")
    if set_name and set_name in parameter_sets:
        parameters.update(parameter_sets[set_name])
    parameters.update(entry.get("parameters", {}))
    return parameters


def directive_arguments(entry, parameter_sets):
    """Return the validated argument names for a directive (None when dynamic)."""
    if entry.get("dynamic_parameters"):
        return None
    return sorted(resolve_parameters(entry, parameter_sets))


def _mode_value(value):
    """Collapse a possibly mode-keyed value to a single string (prefer report)."""
    if isinstance(value, dict):
        value = value.get("report") or value.get("page") or next(iter(value.values()))
    return value


def dispatch_containers(path=MARKDOWN_UTIL_PY):
    """Return the set of directive names dispatched in markdown_util.py.

    Harvests both the ``container == "x"`` and ``container in ["x", "y"]`` forms so
    the coverage check tracks every dispatch branch.
    """
    with open(path) as f:
        source = f.read()
    names = set(re.findall(r'container == "([a-z_]+)"', source))
    for group in re.findall(r"container in \[([^\]]+)\]", source):
        names.update(re.findall(r'"([a-z_]+)"', group))
    return names


def consistency_errors(shared_arguments, parameter_sets, directives, containers):
    """Return human-readable problems with directives.yml or its backend dispatch."""
    errors = []

    for name, entry in directives.items():
        set_name = entry.get("parameter_set")
        if set_name and set_name not in parameter_sets:
            errors.append(f"'{name}': unknown parameter_set '{set_name}'")
        if "requires" not in entry:
            errors.append(f"'{name}': missing 'requires'")
        if "category" not in entry:
            errors.append(f"'{name}': missing 'category'")
        if entry.get("dynamic_parameters") and entry.get("parameters"):
            errors.append(f"'{name}': dynamic_parameters directives must not list parameters")
        resolved = set(resolve_parameters(entry, parameter_sets))
        for shared in shared_arguments:
            if shared in resolved:
                errors.append(f"'{name}': must not list shared argument '{shared}'")

    yml_names = set(directives)
    for missing in sorted(yml_names - containers):
        errors.append(f"directive '{missing}' has no dispatch branch in markdown_util.py")
    for orphan in sorted(containers - yml_names):
        errors.append(f"markdown_util.py dispatches unknown directive '{orphan}' (missing from directives.yml)")

    return errors


def _py_str(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _py_list(items, indent):
    if not items:
        return "[]"
    pad = " " * indent
    body = "".join(f"{pad}    {_py_str(item)},\n" for item in items)
    return "[\n" + body + f"{pad}]"


def render_python(shared_arguments, parameter_sets, directives):
    """Render the generated validator registry module (markdown_parse consumes this)."""
    lines = [
        "# Generated by scripts/markdown_directives_doc.py from",
        "# client/src/components/Markdown/directives.yml. Do not edit by hand.",
        "# Regenerate with `make client-gen-markdown-directives`.",
        "",
        "",
        "class DynamicArguments:",
        "    pass",
        "",
        "",
        "DYNAMIC_ARGUMENTS = DynamicArguments()",
        f"SHARED_ARGUMENTS: list[str] = {_py_list(list(shared_arguments), 0)}",
        "VALID_ARGUMENTS: dict[str, list[str] | DynamicArguments] = {",
    ]
    for name in sorted(directives):
        args = directive_arguments(directives[name], parameter_sets)
        rendered = "DYNAMIC_ARGUMENTS" if args is None else _py_list(args, 4)
        lines.append(f"    {_py_str(name)}: {rendered},")
    lines.append("}")

    embeddable = [name for name, entry in directives.items() if entry.get("embeddable")]
    lines.append(f"EMBED_CAPABLE_DIRECTIVES: list[str] = {_py_list(embeddable, 0)}")
    return "\n".join(lines) + "\n"


def render_requirements(directives):
    """Render requirements.yml (object -> directives) from each directive's 'requires'."""
    grouped: dict[str, list[str]] = {}
    for name, entry in directives.items():
        grouped.setdefault(entry.get("requires", "none"), []).append(name)
    lines = []
    for obj, names in grouped.items():
        lines.append(f"{obj}:")
        for name in names:
            lines.append(f"  - {name}")
    return "\n".join(lines) + "\n"


def _display_width(text):
    """Display width matching prettier/string-width (wide East Asian + emoji count as 2)."""
    width = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return width


def _table(headers, rows):
    """Render a GitHub Markdown table padded exactly as prettier would format it."""
    columns = list(zip(*([headers] + rows)))
    widths = [max(3, *(_display_width(cell) for cell in column)) for column in columns]

    def _row(cells):
        padded = (cell + " " * (width - _display_width(cell)) for cell, width in zip(cells, widths))
        return "| " + " | ".join(padded) + " |"

    lines = [_row(headers), "| " + " | ".join("-" * width for width in widths) + " |"]
    lines.extend(_row(row) for row in rows)
    return "\n".join(lines)


def render_markdown(shared_arguments, parameter_sets, directives):
    """Render directives.yml metadata to the Markdown reference."""
    out = []
    out.append("# Galaxy Markdown Directive Reference")
    out.append("")
    out.append(
        "Generated from `directives.yml` by `scripts/markdown_directives_doc.py` "
        "(`make client-gen-markdown-directives`). Do not edit by hand."
    )
    out.append("")
    out.append("## Syntax")
    out.append("")
    out.append("**Block** — works for every directive; required in workflow report templates:")
    out.append("")
    out.append("````")
    out.append("```galaxy")
    out.append("directive_name(arg=value)")
    out.append("```")
    out.append("````")
    out.append("")
    out.append(
        "One directive per fenced `galaxy` block. **Inline** (`${galaxy ...}`) works only for the "
        "[embeddable directives](#embeddable-directives)."
    )
    out.append("")

    out.append("## Argument value types")
    out.append("")
    present_types = {
        param.get("type")
        for entry in directives.values()
        for param in resolve_parameters(entry, parameter_sets).values()
    }
    rows = [[f"`{t}`", TYPE_NOTES[t]] for t in TYPE_ORDER if t in present_types]
    out.append(_table(["Type", "Meaning"], rows))
    out.append("")

    out.append("## Addressing contexts")
    out.append("")
    out.append("The same directive accepts different parameters depending on how the object is referenced:")
    out.append("")
    present_contexts = {
        param.get("context")
        for entry in directives.values()
        for param in resolve_parameters(entry, parameter_sets).values()
        if param.get("context")
    }
    rows = [[f"`{c}`", CONTEXT_NOTES[c]] for c in CONTEXT_ORDER if c in present_contexts]
    out.append(_table(["Context", "Use"], rows))
    out.append("")

    out.append("## Universal argument")
    out.append("")
    out.append(
        f'`{shared_arguments[0]}="<link text>"` — wraps a block directive in a collapsible section. '
        "Valid on every directive."
    )
    out.append("")

    by_category = {category: [] for category in CATEGORY_ORDER}
    for name, entry in directives.items():
        by_category.setdefault(entry.get("category", "utility"), []).append((name, entry))

    for category in CATEGORY_ORDER:
        entries = by_category.get(category) or []
        if not entries:
            continue
        out.append("---")
        out.append("")
        out.append(f"## {CATEGORY_TITLES[category]}")
        out.append("")
        rows = []
        for name, entry in entries:
            embed = "✅" if entry.get("embeddable") else ""
            requires = entry.get("requires", "none")
            requires_cell = "—" if requires == "none" else f"`{requires}`"
            rows.append([f"`{name}`", embed, requires_cell, entry.get("renders", "")])
        out.append(_table(["Directive", "Embed", "Requires", "Renders"], rows))
        out.append("")

        for name, entry in entries:
            help_text = _mode_value(entry.get("help"))
            parameters = resolve_parameters(entry, parameter_sets)
            dynamic = entry.get("dynamic_parameters")
            if not help_text and not parameters and not dynamic:
                continue
            out.append(f"### `{name}`")
            out.append("")
            if help_text:
                out.append(help_text.replace("%MODE%", "report").strip())
                out.append("")
            if dynamic:
                if not help_text:
                    out.append("Accepts arguments specific to the selected visualization plugin (not validated).")
                    out.append("")
            elif parameters:
                param_rows = []
                for param_name, meta in parameters.items():
                    default = meta.get("default")
                    default_cell = (
                        "" if default is None else f"`{str(default).lower() if isinstance(default, bool) else default}`"
                    )
                    if meta.get("type") == "enum" and meta.get("values"):
                        type_cell = "enum (" + ", ".join(f"`{v}`" for v in meta["values"]) + ")"
                    else:
                        type_cell = f"`{meta.get('type', '')}`"
                    param_rows.append(
                        [
                            f"`{param_name}`",
                            type_cell,
                            f"`{meta['context']}`" if meta.get("context") else "",
                            default_cell,
                            meta.get("description", ""),
                        ]
                    )
                out.append(_table(["Parameter", "Type", "Context", "Default", "Description"], param_rows))
                out.append("")

    out.append("---")
    out.append("")
    out.append("## Embeddable directives")
    out.append("")
    out.append("Inline `${galaxy ...}` syntax is supported only for these directives; all others require block syntax.")
    out.append("")
    for name, entry in directives.items():
        if entry.get("embeddable"):
            out.append(f"- `{name}`")

    return "\n".join(out)


def build_artifacts(shared_arguments, parameter_sets, directives):
    """Return [(path, rendered_text)] for every artifact generated from directives.yml."""
    return [
        (OUTPUT_MD, render_markdown(shared_arguments, parameter_sets, directives) + "\n"),
        (REQUIREMENTS_YML, render_requirements(directives)),
        (GENERATED_PY, render_python(shared_arguments, parameter_sets, directives)),
    ]


def _write_or_check(path, rendered, check, drift):
    try:
        with open(path) as f:
            current = f.read()
    except FileNotFoundError:
        current = None
    if check:
        if current != rendered:
            drift.append(path)
        return
    with open(path, "w") as f:
        f.write(rendered)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify generated artifacts are up to date")
    args = parser.parse_args()

    shared_arguments, parameter_sets, directives = load_directives()
    containers = dispatch_containers()

    errors = consistency_errors(shared_arguments, parameter_sets, directives, containers)
    if errors:
        sys.stderr.write("directives.yml is inconsistent:\n")
        for error in errors:
            sys.stderr.write(f"  - {error}\n")
        sys.exit(1)

    drift: list[str] = []
    for path, rendered in build_artifacts(shared_arguments, parameter_sets, directives):
        _write_or_check(path, rendered, args.check, drift)

    if drift:
        for path in drift:
            sys.stderr.write(f"{path} is out of date; regenerate with `make client-gen-markdown-directives`\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
