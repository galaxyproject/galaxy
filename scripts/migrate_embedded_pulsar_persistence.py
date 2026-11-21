#!/usr/bin/env python
"""Move embedded Pulsar active job index entries into per-handler persistence directories.

Each job handler process loading an embedded Pulsar runner builds its own Pulsar app, which
monitors and recovers every job indexed in its persistence directory. The default persistence
directory is ``<data_dir>/pulsar_persisted_data/<server_name>``; earlier Galaxy releases used
``<data_dir>/pulsar_persisted_data`` itself, shared by all handlers. This script moves every entry
indexed in a shared directory to the directory of the handler its Galaxy job is assigned to.

Stop all Galaxy job handlers before running it. For a Pulsar app configuration that sets
``persistence_directory``, pass the old value as ``--source`` and the new one, containing
``{server_name}``, as ``--target``.
"""

import argparse
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

import galaxy.config
from galaxy.jobs.runners.pulsar import (
    EMBEDDED_PULSAR_PERSISTENCE_DIRECTORY,
    migrate_embedded_pulsar_persistence,
    SERVER_NAME_PLACEHOLDER,
)
from galaxy.model.mapping import init_models_from_config
from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    populate_config_args(parser)
    parser.add_argument(
        "--source",
        help=f"Shared persistence directory (default: <data_dir>/{EMBEDDED_PULSAR_PERSISTENCE_DIRECTORY})",
    )
    parser.add_argument(
        "--target",
        help=f"Per-handler persistence directory containing {SERVER_NAME_PLACEHOLDER} (default: <source>/{SERVER_NAME_PLACEHOLDER})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report what would be moved without moving anything")
    args = parser.parse_args(argv)

    config = galaxy.config.Configuration(**app_properties_from_args(args))
    source = args.source or os.path.join(config.data_dir, EMBEDDED_PULSAR_PERSISTENCE_DIRECTORY)
    target = args.target or os.path.join(source, SERVER_NAME_PLACEHOLDER)
    if SERVER_NAME_PLACEHOLDER not in target:
        parser.error(f"--target must contain {SERVER_NAME_PLACEHOLDER}")

    session = init_models_from_config(config).session
    migrations = migrate_embedded_pulsar_persistence(session, source, target, dry_run=args.dry_run)
    verb = "Would move" if args.dry_run else "Moved"
    for migration in migrations:
        if migration.destination:
            print(f"{verb} {migration.entry} -> {migration.destination}")
        else:
            print(f"Left {migration.entry}: {migration.reason}")
    if not migrations:
        print(f"No active job entries found in {source}")
    elif any(migration.destination is None for migration in migrations):
        print("No handler recovers the entries left in place. Delete them once you have checked them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
