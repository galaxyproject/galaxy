#!/usr/bin/env python3
"""
Script to validate file sources configuration by attempting to create instances
of each configured file source.

This script loads the currently configured file_sources_config_file YAML file
and tries to instantiate each of the specified file sources in order to validate
the configuration models.
"""

import argparse
import os
import sys
import traceback
from typing import (
    Dict,
    List,
    Optional,
)

import yaml

from galaxy.files.models import FileSourcePluginsConfig
from galaxy.files.plugins import FileSourcePluginLoader
from galaxy.files.sources import BaseFilesSource


class Colors:
    """ANSI color codes for terminal output"""

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Apply color to text if stdout is a TTY"""
        if sys.stdout.isatty():
            return f"{color}{text}{cls.RESET}"
        return text

    @classmethod
    def success(cls, text: str) -> str:
        return cls.colorize(text, cls.GREEN)

    @classmethod
    def error(cls, text: str) -> str:
        return cls.colorize(text, cls.RED)

    @classmethod
    def warning(cls, text: str) -> str:
        return cls.colorize(text, cls.YELLOW)

    @classmethod
    def info(cls, text: str) -> str:
        return cls.colorize(text, cls.BLUE)

    @classmethod
    def bold(cls, text: str) -> str:
        return cls.colorize(text, cls.BOLD)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Validate file sources configuration by instantiating each configured file source"
    )
    parser.add_argument(
        "--config-file",
        "-c",
        help="Path to Galaxy configuration file (galaxy.yml). If not provided, will use standard discovery.",
    )
    parser.add_argument(
        "--file-sources-config",
        "-f",
        help="Path to file sources configuration file. If not provided, will use the value from Galaxy config.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output including successful validations",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Exit immediately on first validation error",
    )
    return parser.parse_args()


def find_galaxy_config(config_file: Optional[str] = None) -> Optional[str]:
    """Find the Galaxy configuration file"""
    if config_file and os.path.exists(config_file):
        return config_file

    # Try standard locations
    possible_configs = [
        "../config/galaxy.yml",
        "config/galaxy.yml",
        "galaxy.yml",
        "../config/galaxy.yml.sample",
        "config/galaxy.yml.sample",
    ]

    for config_path in possible_configs:
        if os.path.exists(config_path):
            return config_path

    return None


def load_file_sources_config(config_path: str) -> List[Dict]:
    """Load file sources configuration from YAML file"""
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        if not isinstance(config, list):
            raise ValueError(f"File sources config should be a list, got {type(config)}")

        return config
    except Exception as e:
        print(Colors.error(f"Error loading file sources config from {config_path}: {e}"))
        sys.exit(1)


def validate_file_source_config(
    file_source_config: Dict,
    plugin_loader: FileSourcePluginLoader,
    file_sources_config: FileSourcePluginsConfig,
    verbose: bool = False,
) -> bool:
    """
    Validate a single file source configuration by trying to instantiate it.
    Returns True if valid, False if invalid.
    """
    file_source_id = file_source_config.get("id", "unknown")
    file_source_type = file_source_config.get("type", "unknown")

    try:
        # Get the plugin class for this file source type
        plugin_class = plugin_loader.get_plugin_type_class(file_source_type)

        if verbose:
            print(f"  Validating file source '{file_source_id}' of type '{file_source_type}'...")

        # Create a copy of config with extra kwargs
        plugin_kwds = file_source_config.copy()
        plugin_kwds.update({"file_sources_config": file_sources_config})

        if verbose:
            print("    Using configuration:")
            yaml_str = yaml.dump(file_source_config, default_flow_style=False, sort_keys=False, indent=2)
            indented_yaml = "\n".join(" " * 8 + line if line.strip() else "" for line in yaml_str.splitlines())
            print(Colors.info(indented_yaml))

        # Try to instantiate the file source using the same pattern as the plugin loader
        # Check if this plugin uses the configurable plugin pattern
        configurable_instance = None
        try:
            if hasattr(plugin_class, "build_template_config"):
                configurable_instance = plugin_class
        except TypeError:
            pass

        if configurable_instance:
            # Use the template config pattern
            plugin_template_config = configurable_instance.build_template_config(**plugin_kwds)
            file_source = configurable_instance(template_config=plugin_template_config)
        else:
            # Use direct instantiation
            file_source = plugin_class(**plugin_kwds)

        # Verify it's a valid file source
        if not isinstance(file_source, BaseFilesSource):
            raise ValueError("Plugin did not return a valid BaseFilesSource instance")

        if verbose:
            print(
                f"    {Colors.success('✓ Valid')}: File source '{Colors.bold(file_source_id)}' ({file_source_type}) configured successfully"
            )

        return True

    except KeyError as e:
        print(
            f"    {Colors.error('✗ Error')}: Unknown file source type '{Colors.bold(file_source_type)}' for file source '{Colors.bold(file_source_id)}': {e}"
        )
        return False
    except Exception as e:
        print(
            f"    {Colors.error('✗ Error')}: Failed to validate file source '{Colors.bold(file_source_id)}' ({file_source_type}): {e}"
        )
        if verbose:
            traceback.print_exc()
        return False


def main():
    args = parse_arguments()

    print(Colors.bold("Galaxy File Sources Configuration Validator"))
    print(Colors.bold("=" * 45))

    # Find Galaxy configuration file
    galaxy_config_path = find_galaxy_config(args.config_file)
    if not galaxy_config_path:
        print(Colors.error("Error: Could not find Galaxy configuration file"))
        print("Try specifying it with --config-file option")
        sys.exit(1)

    print(f"Using Galaxy config: {Colors.info(galaxy_config_path)}")

    # Load Galaxy configuration to get file sources config path
    if args.file_sources_config:
        file_sources_config_path = args.file_sources_config
    else:
        # Try to determine from Galaxy config
        try:
            # Simple approach: look for file_sources_config_file in galaxy.yml
            with open(galaxy_config_path) as f:
                galaxy_config = yaml.safe_load(f)

            galaxy_section = galaxy_config.get("galaxy", {})
            file_sources_config_file = galaxy_section.get("file_sources_config_file", "file_sources_conf.yml")

            # Resolve relative to config directory
            config_dir = os.path.dirname(galaxy_config_path)
            file_sources_config_path = os.path.join(config_dir, file_sources_config_file)

        except Exception as e:
            print(Colors.error(f"Error reading Galaxy config: {e}"))
            # Fall back to default
            file_sources_config_path = "config/file_sources_conf.yml"

    if not os.path.exists(file_sources_config_path):
        print(Colors.error(f"Error: File sources config file not found: {file_sources_config_path}"))
        sys.exit(1)

    print(f"Using file sources config: {Colors.info(file_sources_config_path)}")
    print()

    # Load file sources configuration
    file_sources_list = load_file_sources_config(file_sources_config_path)
    print(f"Found {Colors.bold(str(len(file_sources_list)))} file source(s) to validate")

    if not file_sources_list:
        print(Colors.warning("No file sources found in configuration"))
        sys.exit(0)

    # Create plugin loader and file sources config
    plugin_loader = FileSourcePluginLoader()
    file_sources_config = FileSourcePluginsConfig()

    # Validate each file source
    total_count = len(file_sources_list)
    valid_count = 0
    error_count = 0

    print()
    for i, file_source_config in enumerate(file_sources_list, 1):
        if args.verbose:
            print(f"[{Colors.bold(f'{i}/{total_count}')}] Validating file source configuration...")

        is_valid = validate_file_source_config(
            file_source_config, plugin_loader, file_sources_config, verbose=args.verbose
        )

        if is_valid:
            valid_count += 1
        else:
            error_count += 1
            if args.fail_fast:
                print(f"\n{Colors.warning('Failing fast due to --fail-fast option')}")
                sys.exit(1)
        if args.verbose:
            print()

    # Print summary
    print()
    print(Colors.bold("Validation Summary:"))
    print(f"  Total file sources: {Colors.bold(str(total_count))}")
    print(f"  Valid: {Colors.success(str(valid_count))}")
    print(f"  Errors: {Colors.error(str(error_count))}")

    if error_count > 0:
        print(f"\n{Colors.error('✗ Validation failed')}: {error_count} file source(s) have configuration errors")
        sys.exit(1)
    else:
        print(f"\n{Colors.success('✓ All file sources validated successfully!')}")
        sys.exit(0)


if __name__ == "__main__":
    main()
