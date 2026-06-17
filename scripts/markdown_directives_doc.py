#!/usr/bin/env python
"""Generate the Galaxy Markdown directive reference from directives.yml.

directives.yml is the source of truth for directive documentation metadata. This
script renders it to a Markdown reference (directives.md) and can also verify that
the metadata is consistent with the authoritative validator in
``galaxy.managers.markdown_parse`` and that the checked-in reference is up to date.

Usage::

    python scripts/markdown_directives_doc.py            # (re)write directives.md
    python scripts/markdown_directives_doc.py --check     # verify, non-zero exit on drift
"""

import argparse
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

import yaml

from galaxy.managers.markdown_parse import (
    DynamicArguments,
    EMBED_CAPABLE_DIRECTIVES,
    SHARED_ARGUMENTS,
    VALID_ARGUMENTS,
)

MARKDOWN_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "client", "src", "components", "Markdown")
)
DIRECTIVES_YML = os.path.join(MARKDOWN_DIR, "directives.yml")
REQUIREMENTS_YML = os.path.join(MARKDOWN_DIR, "Utilities", "requirements.yml")
OUTPUT_MD = os.path.join(MARKDOWN_DIR, "directives.md")

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
    """Return (parameter_sets, directives) parsed from directives.yml."""
    with open(path) as f:
        data = yaml.safe_load(f)
    parameter_sets = data.get("_parameter_sets", {})
    directives = {key: value for key, value in data.items() if not key.startswith("_")}
    return parameter_sets, directives


def load_requirements(path=REQUIREMENTS_YML):
    """Return a mapping of directive -> required object from requirements.yml."""
    with open(path) as f:
        data = yaml.safe_load(f)
    requires = {}
    for obj, directives in data.items():
        for directive in directives:
            requires[directive] = obj
    return requires


def resolve_parameters(entry, parameter_sets):
    """Merge a directive's shared parameter_set and inline parameters, preserving order."""
    parameters = {}
    set_name = entry.get("parameter_set")
    if set_name and set_name in parameter_sets:
        parameters.update(parameter_sets[set_name])
    parameters.update(entry.get("parameters", {}))
    return parameters


def _mode_value(value):
    """Collapse a possibly mode-keyed value to a single string (prefer report)."""
    if isinstance(value, dict):
        value = value.get("report") or value.get("page") or next(iter(value.values()))
    return value


def consistency_errors(parameter_sets, directives, requirements):
    """Return a list of human-readable mismatches between directives.yml and the validator."""
    errors = []

    yml_names = set(directives)
    valid_names = set(VALID_ARGUMENTS)
    for missing in sorted(valid_names - yml_names):
        errors.append(f"directives.yml is missing an entry for directive '{missing}'")
    for extra in sorted(yml_names - valid_names):
        errors.append(f"directives.yml has entry for unknown directive '{extra}'")

    for name in sorted(yml_names & valid_names):
        entry = directives[name]

        set_name = entry.get("parameter_set")
        if set_name and set_name not in parameter_sets:
            errors.append(f"'{name}': unknown parameter_set '{set_name}'")

        expected_embed = name in EMBED_CAPABLE_DIRECTIVES
        if bool(entry.get("embeddable")) != expected_embed:
            errors.append(f"'{name}': embeddable should be {str(expected_embed).lower()}")

        expected_requires = requirements.get(name, "none")
        if entry.get("requires") != expected_requires:
            errors.append(f"'{name}': requires should be '{expected_requires}'")

        valid_args = VALID_ARGUMENTS[name]
        if isinstance(valid_args, DynamicArguments):
            if not entry.get("dynamic_parameters"):
                errors.append(f"'{name}': should set dynamic_parameters: true")
            continue

        resolved = set(resolve_parameters(entry, parameter_sets))
        expected_args = set(valid_args)
        if SHARED_ARGUMENTS[0] in resolved:
            errors.append(f"'{name}': must not list shared argument '{SHARED_ARGUMENTS[0]}'")
        for missing in sorted(expected_args - resolved):
            errors.append(f"'{name}': missing parameter '{missing}'")
        for extra in sorted(resolved - expected_args):
            errors.append(f"'{name}': parameter '{extra}' is not accepted by the validator")

    return errors


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_markdown(parameter_sets, directives):
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
        f'`{SHARED_ARGUMENTS[0]}="<link text>"` — wraps a block directive in a collapsible section. '
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
    for name in EMBED_CAPABLE_DIRECTIVES:
        out.append(f"- `{name}`")

    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify consistency and up-to-date output")
    parser.add_argument("--output", default=OUTPUT_MD, help="output path for directives.md")
    args = parser.parse_args()

    parameter_sets, directives = load_directives()
    requirements = load_requirements()

    errors = consistency_errors(parameter_sets, directives, requirements)
    if errors:
        sys.stderr.write("directives.yml is inconsistent with markdown_parse.py:\n")
        for error in errors:
            sys.stderr.write(f"  - {error}\n")
        sys.exit(1)

    rendered = render_markdown(parameter_sets, directives) + "\n"

    if args.check:
        try:
            with open(args.output) as f:
                current = f.read()
        except FileNotFoundError:
            current = None
        if current != rendered:
            sys.stderr.write(f"{args.output} is out of date; regenerate with scripts/markdown_directives_doc.py\n")
            sys.exit(1)
        return

    with open(args.output, "w") as f:
        f.write(rendered)


if __name__ == "__main__":
    main()
