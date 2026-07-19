"""Build portable seed data for Galaxy's persistent mulled resolution cache."""

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

QUAY_REPOSITORY_API_ENDPOINT = "https://quay.io/api/v1/repository"
FetchJson = Callable[[str, dict[str, str]], dict[str, Any]]


def _fetch_json(endpoint: str, parameters: dict[str, str]) -> dict[str, Any]:
    url = f"{endpoint}?{urllib.parse.urlencode(parameters)}"
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def quay_repositories(namespace: str, fetch_json: FetchJson = _fetch_json) -> list[str]:
    """Return all public repository names in a Quay namespace."""
    repositories: list[str] = []
    next_page = None
    while True:
        parameters = {"public": "true", "namespace": namespace}
        if next_page:
            parameters["next_page"] = next_page
        page = fetch_json(QUAY_REPOSITORY_API_ENDPOINT, parameters)
        repositories.extend(repository["name"] for repository in page["repositories"])
        next_page = page.get("next_page")
        if not next_page:
            return repositories


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
