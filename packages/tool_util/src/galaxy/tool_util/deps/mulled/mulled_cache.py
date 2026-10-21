"""Build portable seed data for Galaxy's persistent mulled resolution cache."""

import argparse
import json
import os

from galaxy.tool_util.deps.mulled.util import quay_repositories


def write_cache_seed(output: str, namespace: str) -> None:
    repositories = quay_repositories(namespace)
    output = os.path.abspath(output)
    os.makedirs(os.path.dirname(output), exist_ok=True)
    temporary_output = f"{output}.tmp"
    with open(temporary_output, "w") as seed_file:
        json.dump({"namespace": namespace, "repositories": repositories}, seed_file)
    os.replace(temporary_output, output)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build a portable seed for Galaxy's mulled resolution cache.")
    parser.add_argument("--namespace", default="biocontainers", help="Quay namespace to index.")
    parser.add_argument("--output", required=True, help="Path to the JSON seed file.")
    args = parser.parse_args(argv)
    write_cache_seed(args.output, args.namespace)


if __name__ == "__main__":
    main()
