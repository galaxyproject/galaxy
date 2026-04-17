"""Admin CLI for the GTN search database.

Run as ``python -m galaxy.agents.gtn --refresh`` from within a Galaxy
virtualenv to force-redownload the published database. Admins who have
relocated the database via ``gtn_database_path`` should pass ``--path``.
"""

import argparse
import logging
import sys

from .search import (
    GTN_DATABASE_URL,
    GTNSearchDB,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="GTN search database admin operations")
    parser.add_argument("--refresh", action="store_true", help="Force-redownload the database")
    parser.add_argument("--path", help="Database path (overrides built-in default)")
    parser.add_argument("--url", default=GTN_DATABASE_URL, help="Download URL (overrides default)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    if not args.refresh:
        parser.error("no action specified; pass --refresh to redownload the database")

    db = GTNSearchDB(db_path=args.path, download_url=args.url)
    db.refresh()
    return 0


if __name__ == "__main__":
    sys.exit(main())
