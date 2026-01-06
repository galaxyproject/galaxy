"""
Fix tool_config paths in Tool Shed repository metadata.

This script updates tool_config paths in RepositoryMetadata that reference an old
file_path location. When the Tool Shed's file_path configuration changes, tool_config
paths in the metadata may become invalid. This script identifies invalid paths and
updates them to use the current file_path configuration.

Run this script from the root folder:

$ python scripts/tool_shed/fix_tool_config_paths.py -c config/tool_shed.yml --dry-run

Options:
  -c, --config        Path to Tool Shed configuration file (required)
  --dry-run          Report changes without modifying database
  -d, --debug        Enable debug logging
  --backup-dir       Directory to save original metadata JSON files (default: ./metadata_backups)

This script expects the Tool Shed's runtime virtualenv to be active.
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "lib")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args,
)
from tool_shed.webapp import config as ts_config
from tool_shed.webapp.model import RepositoryMetadata

log = logging.getLogger()
log.addHandler(logging.StreamHandler(sys.stdout))


class PathFixerStats:
    """Track statistics for the path fixing operation."""

    def __init__(self):
        self.total_repo_metadata = 0
        self.repo_metadata_with_tools = 0
        self.total_tools = 0
        self.invalid_paths = 0
        self.updated_paths = 0
        self.paths_with_existing_files = 0
        self.paths_with_missing_files = 0
        self.already_valid_paths = 0
        self.unfixable_paths = 0  # Kept for errors in path construction

    def print_summary(self):
        """Print a summary of the statistics."""
        log.info("=" * 70)
        log.info("SUMMARY")
        log.info("=" * 70)
        log.info(f"Total RepositoryMetadata records processed: {self.total_repo_metadata}")
        log.info(f"RepositoryMetadata with tools: {self.repo_metadata_with_tools}")
        log.info(f"Total tools examined: {self.total_tools}")
        log.info(f"Tools with correct paths (unchanged): {self.already_valid_paths}")
        log.info(f"Tools with paths updated: {self.updated_paths}")
        log.info(f"  - Tool file exists on disk: {self.paths_with_existing_files}")
        log.info(f"  - Tool file missing (removed in later changeset): {self.paths_with_missing_files}")
        log.info(f"Tools with path construction errors: {self.unfixable_paths}")
        log.info("=" * 70)


def construct_new_path(old_path, repository, current_file_path):
    """
    Extract the repository-relative portion from old path and join with new file_path.

    Pattern: ${hash_dirs}/repo_${id}/relative_tool_path
    Example: 000/repo_123/filtering.xml

    Args:
        old_path: The old absolute path to the tool config
        repository: Repository object
        current_file_path: Current file_path configuration value

    Returns:
        str: The new path constructed with current file_path
    """
    # Get expected repository directory using the repository's method
    expected_repo_path = repository.hg_repository_path(current_file_path)

    # Extract the portion after "repo_{id}/" to get the relative tool path
    if (repo_pattern := f"repo_{repository.id}/") in old_path:
        # Split on the repo pattern and take everything after it
        relative_tool_path = old_path.split(repo_pattern, 1)[1]
        new_path = os.path.join(expected_repo_path, relative_tool_path)
        return new_path

    # Fallback: try to extract using regex pattern for hash_dirs/repo_id/file
    # Pattern matches: .../000/repo_123/tool.xml or .../000/123/456/repo_789/tool.xml
    pattern = r".*/(\d+/)*(repo_\d+/.*)"

    if match := re.search(pattern, old_path):
        # Extract everything from "repo_" onward
        repo_relative = match.group(2)  # e.g., "repo_123/filtering.xml"

        # Verify the repo_id matches
        repo_id_match = re.search(r"repo_(\d+)/", repo_relative)
        if repo_id_match and int(repo_id_match.group(1)) == repository.id:
            # Extract just the file path after repo_id
            relative_tool_path = repo_relative.split("/", 1)[1] if "/" in repo_relative else ""
            new_path = os.path.join(expected_repo_path, relative_tool_path)
            return new_path

    # Final fallback: use repository's expected path + filename only
    filename = os.path.basename(old_path)
    new_path = os.path.join(expected_repo_path, filename)
    log.debug(f"Using fallback (filename only) for path construction: {old_path} -> {new_path}")

    return new_path


def save_metadata_backup(repo_metadata, backup_dir):
    """
    Save original metadata to JSON file.

    Args:
        repo_metadata: RepositoryMetadata object
        backup_dir: Directory to save backup files
    """
    os.makedirs(backup_dir, exist_ok=True)

    filename = f"repo_metadata_{repo_metadata.id}_{repo_metadata.changeset_revision}.json"
    filepath = os.path.join(backup_dir, filename)

    backup_data = {
        "id": repo_metadata.id,
        "repository_id": repo_metadata.repository_id,
        "changeset_revision": repo_metadata.changeset_revision,
        "metadata": repo_metadata.metadata,
        "backup_time": datetime.now().isoformat(),
    }

    with open(filepath, "w") as f:
        json.dump(backup_data, f, indent=2)

    log.debug(f"Saved metadata backup to {filepath}")


def report_change(repo_metadata, tool, old_path, new_path, tool_file_exists, stats):
    """
    Report a path change in dry-run mode.

    Args:
        repo_metadata: RepositoryMetadata object
        tool: Tool dictionary from metadata
        old_path: Old tool_config path
        new_path: New tool_config path
        tool_file_exists: Whether the specific tool file exists on disk
        stats: PathFixerStats object
    """
    file_status = "FILE EXISTS" if tool_file_exists else "FILE MISSING (removed in later changeset)"
    tool_id = tool.get("id", "unknown")
    tool_name = tool.get("name", "unknown")

    log.info(
        f"[REPO_METADATA {repo_metadata.id}] Tool '{tool_id}' ({tool_name}):\n"
        f"  OLD: {old_path}\n"
        f"  NEW: {new_path}\n"
        f"  STATUS: {file_status}"
    )

    stats.updated_paths += 1
    if tool_file_exists:
        stats.paths_with_existing_files += 1
    else:
        stats.paths_with_missing_files += 1


def process_repository_metadata(session, current_file_path, dry_run, backup_dir, stats):
    """
    Process all RepositoryMetadata records and fix tool_config paths.

    Args:
        session: SQLAlchemy session
        current_file_path: Current file_path configuration value
        dry_run: If True, only report changes without modifying database
        backup_dir: Directory to save metadata backups
        stats: PathFixerStats object
    """
    log.info(f"Current file_path: {current_file_path}")
    log.info(f"Backup directory: {backup_dir}")
    log.info(f"Dry run mode: {dry_run}")
    log.info("-" * 70)

    # Load all RepositoryMetadata items
    repo_metadata_list = session.query(RepositoryMetadata).all()
    stats.total_repo_metadata = len(repo_metadata_list)

    log.info(f"Found {stats.total_repo_metadata} RepositoryMetadata records")

    for repo_metadata in repo_metadata_list:
        # Skip if no metadata or no tools
        if not repo_metadata.metadata or "tools" not in repo_metadata.metadata:
            continue

        stats.repo_metadata_with_tools += 1
        tools = repo_metadata.metadata.get("tools", [])
        modified = False

        # Get the repository directory path (ending with repo_${id})
        try:
            repo_dir = repo_metadata.repository.hg_repository_path(current_file_path)
            repo_dir_exists = os.path.exists(repo_dir)
        except Exception as e:
            log.error(f"[REPO_METADATA {repo_metadata.id}] Error getting repository path: {e}")
            continue

        if not repo_dir_exists:
            log.warning(
                f"[REPO_METADATA {repo_metadata.id}] Repository directory does not exist: {repo_dir}. "
                f"Skipping all tools for this repository."
            )
            continue

        for tool in tools:
            stats.total_tools += 1

            old_path = tool.get("tool_config")
            if not old_path:
                log.debug(f"[REPO_METADATA {repo_metadata.id}] Tool has no tool_config: {tool.get('id')}")
                continue

            # Construct expected new path
            try:
                new_path = construct_new_path(old_path, repo_metadata.repository, current_file_path)
            except Exception as e:
                log.error(f"[REPO_METADATA {repo_metadata.id}] Error constructing new path for {old_path}: {e}")
                stats.unfixable_paths += 1
                continue

            # Check if this is already using the correct base path
            if old_path == new_path:
                log.debug(f"[REPO_METADATA {repo_metadata.id}] Path already correct: {old_path}")
                stats.already_valid_paths += 1
                continue

            # Path needs updating
            stats.invalid_paths += 1

            # Check if the specific tool file exists (for informational purposes only)
            tool_file_exists = os.path.exists(new_path)

            # Report or update
            if dry_run:
                report_change(repo_metadata, tool, old_path, new_path, tool_file_exists, stats)
            else:
                file_status_msg = (
                    "tool file exists"
                    if tool_file_exists
                    else "tool file missing - may have been removed in later changeset"
                )
                log.info(
                    f"[REPO_METADATA {repo_metadata.id}] Updating tool '{tool.get('id')}': "
                    f"{old_path} -> {new_path} ({file_status_msg})"
                )
                tool["tool_config"] = new_path
                modified = True
                stats.updated_paths += 1
                if tool_file_exists:
                    stats.paths_with_existing_files += 1
                else:
                    stats.paths_with_missing_files += 1

        # Save changes if modified (SQLAlchemy change detection for MutableJSONType)
        if modified and not dry_run:
            # Reassign the metadata dict to trigger SQLAlchemy's change detection
            repo_metadata.metadata = repo_metadata.metadata.copy()

        # Always backup original metadata if there were tools
        if tools:
            save_metadata_backup(repo_metadata, backup_dir)

    log.info("-" * 70)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Fix tool_config paths in Tool Shed repository metadata after file_path config changes."
    )
    populate_config_args(parser)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report changes without modifying the database",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug logging",
    )
    parser.add_argument(
        "--backup-dir",
        type=str,
        default="./metadata_backups",
        help="Directory to save original metadata JSON files (default: ./metadata_backups)",
    )
    args = parser.parse_args()

    # Setup logging first
    if args.debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    # Log the config file being used
    config_file = getattr(args, "config_file", None)
    log.info(f"Loading configuration from: {config_file}")

    # Set config section to 'tool_shed'
    args.config_section = "tool_shed"

    # Load Tool Shed configuration
    app_properties = app_properties_from_args(args)

    # Log what properties were loaded
    if args.debug:
        log.debug("Loaded app_properties:")
        for key, value in sorted(app_properties.items()):
            log.debug(f"  {key}: {value}")

    config = ts_config.ToolShedAppConfiguration(**app_properties)

    # Add config values to args
    args.dburi = config.database_connection
    args.file_path = config.file_path

    # Log final config values
    if args.debug:
        log.debug("Final configuration:")
        log.debug(f"  Config file: {config_file}")
        log.debug(f"  Database: {args.dburi}")
        log.debug(f"  File path: {args.file_path}")
        log.debug(f"  Dry run: {args.dry_run}")
        log.debug(f"  Backup dir: {args.backup_dir}")

    return args


def main():
    """Main entry point."""
    args = parse_arguments()

    # Setup database session
    engine = create_engine(args.dburi)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Initialize statistics
    stats = PathFixerStats()

    try:
        # Process all repository metadata
        process_repository_metadata(
            session=session,
            current_file_path=args.file_path,
            dry_run=args.dry_run,
            backup_dir=args.backup_dir,
            stats=stats,
        )

        # Commit changes if not in dry-run mode
        if not args.dry_run:
            session.commit()
            log.info("Changes committed to database")
        else:
            log.info("Dry run complete - no changes made to database")

    except Exception as e:
        log.error(f"Error during processing: {e}")
        session.rollback()
        raise
    finally:
        session.close()

    # Print summary
    stats.print_summary()


if __name__ == "__main__":
    main()
