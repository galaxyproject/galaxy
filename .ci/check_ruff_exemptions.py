#!/usr/bin/env python
"""Remove obsolete file/rule entries from Ruff's annotation baseline."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START = "# >>> ruff-annotation-exemptions (generated) >>>"
END = "# <<< ruff-annotation-exemptions <<<"


def prune(config: Path, ruff: str, *, fix: bool = False, summary: Path | None = None) -> int:
    source = config.read_text()
    before, section = source.split(START + "\n", 1)
    baseline, after = section.split(END, 1)
    entries = {}
    for line in baseline.splitlines():
        if line.startswith('"'):
            path, rules = line.split(" = ", 1)
            entries[json.loads(path)] = set(json.loads(rules))

    # Keep policy exemptions (such as tests) and all other settings. The
    # temporary config stays beside the original so relative paths still work.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", dir=config.parent) as temporary:
        temporary.write(before + after)
        temporary.flush()
        result = subprocess.run(
            [
                ruff,
                "check",
                "--config",
                temporary.name,
                "--select",
                "ANN",
                "--ignore",
                "ANN401",
                "--output-format",
                "json",
                ".",
            ],
            cwd=config.parent,
            capture_output=True,
            text=True,
        )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"Ruff failed:\n{result.stdout}{result.stderr}")
    reported = {
        (Path(item["filename"]).relative_to(config.parent).as_posix(), item["code"])
        for item in json.loads(result.stdout)
    }
    exempted = {(path, rule) for path, rules in entries.items() for rule in rules}
    stale = exempted - reported
    missing = reported - exempted
    report = [f"{len(stale)} stale Ruff annotation exemptions."]
    report.extend(f"- `{path}`: `{rule}`" for path, rule in sorted(stale))
    if missing:
        report.append("\nUnexempted annotation violations (fix these before pruning):")
        report.extend(f"- `{path}`: `{rule}`" for path, rule in sorted(missing))
    message = "\n".join(report) + "\n"
    print(message, end="")
    if summary:
        summary.write_text(message)
    if fix and stale and not missing:
        kept = []
        for line in baseline.splitlines():
            if line.startswith('"'):
                path = json.loads(line.split(" = ", 1)[0])
                rules = sorted(rule for rule in entries[path] if (path, rule) in reported)
                if not rules:
                    continue
                line = f"{json.dumps(path)} = {json.dumps(rules)}"
            kept.append(line)
        config.write_text(before + START + "\n" + "\n".join(kept) + "\n" + END + after)
    return int(bool(missing or (stale and not fix)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true", help="remove stale exemptions")
    parser.add_argument("--ruff", default="ruff", help="Ruff executable to use")
    parser.add_argument("--summary", type=Path, help="write a Markdown report")
    args = parser.parse_args()
    return prune(ROOT / "ruff.toml", args.ruff, fix=args.fix, summary=args.summary)


if __name__ == "__main__":
    raise SystemExit(main())
