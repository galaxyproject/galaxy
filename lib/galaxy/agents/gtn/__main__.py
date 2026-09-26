"""Admin CLI for the GTN search database.

Run as ``python -m galaxy.agents.gtn --refresh`` from within a Galaxy
virtualenv to force-redownload the published database. The CLI resolves
``gtn_database_path`` from Galaxy configuration unless ``--path`` is supplied.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from galaxy.config import GalaxyAppConfiguration
from galaxy.util.properties import (
    find_config_file,
    load_app_properties,
)
from .search import (
    GTN_DATABASE_URL,
    GTNSearchDB,
)


def _resolve_config_file(explicit_config_file: str | None) -> str:
    if explicit_config_file:
        config_file = Path(explicit_config_file)
        if not config_file.exists():
            raise RuntimeError(f"Config file does not exist: {config_file}")
        return str(config_file)

    if env_config_file := os.environ.get("GALAXY_CONFIG_FILE"):
        config_file = Path(env_config_file)
        if not config_file.exists():
            raise RuntimeError(f"GALAXY_CONFIG_FILE does not exist: {config_file}")
        return str(config_file)

    config_file = find_config_file("galaxy")
    if not config_file:
        raise RuntimeError("Could not find Galaxy config; pass --path explicitly or provide --config-file.")
    return config_file


def _resolve_database_path(path: str | None, config_file: str | None) -> Path:
    if path:
        return Path(path)

    resolved_config_file = _resolve_config_file(config_file)
    app_properties = load_app_properties(config_file=resolved_config_file)
    galaxy_config = GalaxyAppConfiguration(override_tempdir=False, **app_properties)
    db_path = getattr(galaxy_config, "gtn_database_path", None)
    if not db_path:
        raise RuntimeError("Configured gtn_database_path is empty; pass --path explicitly.")
    return Path(db_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="GTN search database admin operations")
    parser.add_argument("--refresh", action="store_true", help="Force-redownload the database")
    parser.add_argument("--path", help="Database path (overrides built-in default)")
    parser.add_argument("--config-file", help="Galaxy config file used to resolve gtn_database_path")
    parser.add_argument("--url", default=GTN_DATABASE_URL, help="Download URL (overrides default)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    if not args.refresh:
        parser.error("no action specified; pass --refresh to redownload the database")

    try:
        db_path = _resolve_database_path(args.path, args.config_file)
    except RuntimeError as e:
        parser.error(str(e))

    metadata = GTNSearchDB.refresh_database(db_path, args.url)
    logging.info(
        "Refreshed GTN database at %s (version=%s, tutorials=%s, faqs=%s)",
        db_path,
        metadata["version"],
        metadata["tutorial_count"],
        metadata["faq_count"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
