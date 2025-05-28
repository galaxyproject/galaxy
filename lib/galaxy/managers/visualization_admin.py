"""
Manager for visualization package administration.

Handles low-level operations for managing visualization packages including
npm package operations, file system management, and configuration updates.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from glob import glob
from typing import (
    Dict,
    List,
    Optional,
    Union,
)

import requests
import yaml

from galaxy import exceptions
from galaxy.managers.base import ModelManager
from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)


class VisualizationPackageManager(ModelManager):
    """Manager for visualization package operations."""

    model_class = type(None)  # Not managing database models

    def __init__(self, app: MinimalManagerApp):
        super().__init__(app)
        self.config_path = os.path.join(app.config.root, "client", "visualizations.yml")
        self.static_path = os.path.join(app.config.root, "static", "plugins", "visualizations")

        # Ensure directories exist
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        os.makedirs(self.static_path, exist_ok=True)

    def load_config(self) -> Dict:
        """Load the visualizations.yml configuration file."""
        try:
            if not os.path.exists(self.config_path):
                return {}

            with open(self.config_path) as f:
                return yaml.safe_load(f) or {}

        except Exception as e:
            log.error(f"Failed to load visualization config: {e}")
            raise exceptions.InternalServerError(f"Failed to load configuration: {e}")

    def save_config(self, config: Dict) -> None:
        """Save the visualizations.yml configuration file."""
        try:
            with open(self.config_path, "w") as f:
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=True)

        except Exception as e:
            log.error(f"Failed to save visualization config: {e}")
            raise exceptions.InternalServerError(f"Failed to save configuration: {e}")

    def get_package_info(self, viz_id: str) -> Optional[Dict]:
        """Get information about a specific package from config."""
        config = self.load_config()
        return config.get(viz_id)

    def add_package_to_config(self, viz_id: str, package: str, version: str, enabled: bool = True) -> None:
        """Add or update a package in the configuration."""
        config = self.load_config()
        config[viz_id] = {"package": package, "version": version, "enabled": enabled}
        self.save_config(config)

    def remove_package_from_config(self, viz_id: str) -> None:
        """Remove a package from the configuration."""
        config = self.load_config()
        if viz_id in config:
            del config[viz_id]
            self.save_config(config)

    def toggle_package_enabled(self, viz_id: str, enabled: bool) -> None:
        """Enable or disable a package in the configuration."""
        config = self.load_config()

        if viz_id not in config:
            raise exceptions.ObjectNotFound(f"Package '{viz_id}' not found in configuration")

        if isinstance(config[viz_id], dict):
            config[viz_id]["enabled"] = enabled
        else:
            # Convert string entry to dict format
            config[viz_id] = {"package": config[viz_id], "enabled": enabled}

        self.save_config(config)

    def install_npm_package(self, package: str, version: str, target_dir: str) -> Dict:
        """Install an npm package to a target directory."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Install package using npm
                package_spec = f"{package}@{version}"
                cmd = ["npm", "install", package_spec, "--prefix", temp_dir, "--no-audit", "--no-fund", "--production"]

                log.info(f"Installing npm package: {package_spec}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=temp_dir)

                if result.returncode != 0:
                    log.error(f"npm install failed: {result.stderr}")
                    raise exceptions.InternalServerError(f"Package installation failed: {result.stderr}")

                # Find the installed package directory
                package_name = package.split("/")[-1]  # Handle scoped packages like @galaxyproject/foo
                source_path = os.path.join(temp_dir, "node_modules", package_name)

                if not os.path.exists(source_path):
                    # Try full package name for scoped packages
                    source_path = os.path.join(temp_dir, "node_modules", package)

                if not os.path.exists(source_path):
                    raise exceptions.InternalServerError(
                        f"Package directory not found after installation: {source_path}"
                    )

                # Create target directory
                os.makedirs(target_dir, exist_ok=True)

                # Copy package contents
                shutil.copytree(source_path, target_dir, dirs_exist_ok=True)

                # Validate package structure
                self.validate_package_structure(target_dir)

                # Get package metadata
                package_json_path = os.path.join(target_dir, "package.json")
                metadata = {}
                if os.path.exists(package_json_path):
                    with open(package_json_path) as f:
                        metadata = json.load(f)

                return {
                    "package": package,
                    "version": version,
                    "path": target_dir,
                    "size": self.get_directory_size(target_dir),
                    "metadata": metadata,
                }

        except subprocess.TimeoutExpired:
            raise exceptions.InternalServerError("Package installation timed out")
        except Exception as e:
            log.error(f"Failed to install npm package {package}@{version}: {e}")
            raise exceptions.InternalServerError(f"Package installation failed: {e}")

    def validate_package_structure(self, package_dir: str) -> bool:
        """Validate that a package has the required structure for Galaxy visualizations."""
        required_files = ["package.json"]

        for required_file in required_files:
            file_path = os.path.join(package_dir, required_file)
            if not os.path.exists(file_path):
                raise exceptions.ConfigurationError(f"Required file missing: {required_file}")

        # Validate package.json structure
        package_json_path = os.path.join(package_dir, "package.json")
        try:
            with open(package_json_path) as f:
                package_json = json.load(f)

            # Check for required fields
            required_fields = ["name", "version"]
            for field in required_fields:
                if field not in package_json:
                    raise exceptions.ConfigurationError(f"package.json missing required field: {field}")

        except json.JSONDecodeError as e:
            raise exceptions.ConfigurationError(f"Invalid package.json: {e}")

        return True

    def cleanup_package_files(self, viz_id: str) -> None:
        """Remove package files from the static directory."""
        package_dir = os.path.join(self.static_path, viz_id)
        if os.path.exists(package_dir):
            try:
                shutil.rmtree(package_dir)
                log.info(f"Cleaned up package files for {viz_id}")
            except Exception as e:
                log.error(f"Failed to cleanup files for {viz_id}: {e}")
                raise exceptions.InternalServerError(f"Failed to cleanup package files: {e}")

    def get_package_path(self, viz_id: str) -> str:
        """Get the file system path for a package."""
        return os.path.join(self.static_path, viz_id)

    def is_package_installed(self, viz_id: str) -> bool:
        """Check if a package is installed on the file system."""
        package_path = self.get_package_path(viz_id)
        return os.path.exists(package_path) and os.path.isdir(package_path)

    def get_directory_size(self, path: str) -> int:
        """Calculate the total size of a directory in bytes."""
        total_size = 0
        try:
            for dirpath, _dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            log.warning(f"Failed to calculate directory size for {path}: {e}")

        return total_size

    def get_package_metadata(self, viz_id: str) -> Dict:
        """Get metadata from an installed package's package.json."""
        package_path = self.get_package_path(viz_id)
        package_json_path = os.path.join(package_path, "package.json")

        if not os.path.exists(package_json_path):
            return {}

        try:
            with open(package_json_path) as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Failed to read package.json for {viz_id}: {e}")
            return {}

    def query_npm_registry(self, search_term: Optional[str] = None) -> List[Dict]:
        """Query npm registry for @galaxyproject visualization packages."""
        try:
            # Build search URL
            base_url = "https://registry.npmjs.org/-/search"
            query_parts = ["scope:galaxyproject"]

            if search_term:
                query_parts.append(search_term)

            params: Dict[str, Union[str, int]] = {
                "text": " ".join(query_parts),
                "size": 250,  # Maximum results
            }

            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            packages = []

            for result in data.get("objects", []):
                package_info = result.get("package", {})

                # Filter for visualization packages
                keywords = package_info.get("keywords", [])
                if "visualization" in keywords or "galaxy-visualization" in keywords:
                    packages.append(
                        {
                            "name": package_info.get("name", ""),
                            "description": package_info.get("description", ""),
                            "version": package_info.get("version", ""),
                            "keywords": keywords,
                            "author": package_info.get("author", {}),
                            "maintainers": package_info.get("maintainers", []),
                            "links": package_info.get("links", {}),
                            "date": package_info.get("date", ""),
                            "score": result.get("score", {}),
                        }
                    )

            return packages

        except requests.RequestException as e:
            log.error(f"Failed to query npm registry: {e}")
            raise exceptions.InternalServerError(f"Failed to query package registry: {e}")

    def get_package_versions(self, package_name: str) -> List[str]:
        """Get available versions for a specific package from npm registry."""
        try:
            url = f"https://registry.npmjs.org/{package_name}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            versions = list(data.get("versions", {}).keys())

            # Sort versions (basic sort, could be improved with semver)
            versions.sort(reverse=True)

            return versions

        except requests.RequestException as e:
            log.error(f"Failed to get versions for {package_name}: {e}")
            raise exceptions.InternalServerError(f"Failed to get package versions: {e}")

    def backup_config(self) -> Optional[str]:
        """Create a backup of the current configuration."""
        backup_path = f"{self.config_path}.backup"
        try:
            if os.path.exists(self.config_path):
                shutil.copy2(self.config_path, backup_path)
                return backup_path
        except Exception as e:
            log.error(f"Failed to create config backup: {e}")

        return None

    def restore_config(self, backup_path: str) -> None:
        """Restore configuration from a backup."""
        try:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, self.config_path)
                log.info("Configuration restored from backup")
            else:
                raise exceptions.ObjectNotFound("Backup file not found")
        except Exception as e:
            log.error(f"Failed to restore config: {e}")
            raise exceptions.InternalServerError(f"Failed to restore configuration: {e}")

    def stage_all_visualizations(self) -> Dict:
        """
        Stage all visualization assets from config/plugins/visualizations to static/plugins/visualizations.
        This is equivalent to the gulp stagePlugins task.
        """
        try:
            plugins_base_dir = os.path.join(self.app.config.root, "config", "plugins")
            source_patterns = [
                os.path.join(plugins_base_dir, "visualizations", "*", "static"),
                os.path.join(plugins_base_dir, "visualizations", "*", "*", "static"),
            ]

            staged_count = 0
            staged_visualizations = []
            errors = []

            # Find all static directories to stage
            source_dirs = []
            for pattern in source_patterns:
                source_dirs.extend(glob(pattern))

            for source_dir in source_dirs:
                try:
                    # Skip node_modules/.bin directories
                    if "node_modules/.bin" in source_dir:
                        continue

                    # Get the relative path from plugins base dir
                    relative_path = os.path.relpath(source_dir, plugins_base_dir)
                    target_dir = os.path.join(self.app.config.root, "static", "plugins", relative_path)

                    # Create target directory
                    os.makedirs(os.path.dirname(target_dir), exist_ok=True)

                    # Copy the static directory
                    if os.path.exists(target_dir):
                        shutil.rmtree(target_dir)

                    shutil.copytree(source_dir, target_dir, ignore=shutil.ignore_patterns("node_modules/.bin"))

                    staged_count += 1
                    # Extract visualization name from path
                    viz_name = self._extract_viz_name_from_path(relative_path)
                    if viz_name:
                        staged_visualizations.append(viz_name)

                    log.info(f"Staged visualization assets: {relative_path}")

                except Exception as e:
                    error_msg = f"Failed to stage {source_dir}: {e}"
                    log.error(error_msg)
                    errors.append(error_msg)

            return {"staged_count": staged_count, "staged_visualizations": staged_visualizations, "errors": errors}

        except Exception as e:
            log.error(f"Failed to stage visualizations: {e}")
            raise exceptions.InternalServerError(f"Failed to stage visualizations: {e}")

    def stage_visualization(self, viz_id: str) -> Dict:
        """
        Stage assets for a specific visualization from config/plugins to static/plugins.
        """
        try:
            plugins_base_dir = os.path.join(self.app.config.root, "config", "plugins")

            # Look for the visualization in both possible locations
            possible_paths = [
                os.path.join(plugins_base_dir, "visualizations", viz_id, "static"),
                # Check for nested visualizations (like jqplot/jqplot_bar)
                (
                    os.path.join(
                        plugins_base_dir, "visualizations", viz_id.split("/")[0], viz_id.split("/")[-1], "static"
                    )
                    if "/" in viz_id
                    else None
                ),
            ]

            source_dir = None
            for path in possible_paths:
                if path and os.path.exists(path):
                    source_dir = path
                    break

            if not source_dir:
                raise exceptions.ObjectNotFound(f"Static assets not found for visualization '{viz_id}'")

            # Calculate relative path and target
            relative_path = os.path.relpath(source_dir, plugins_base_dir)
            target_dir = os.path.join(self.app.config.root, "static", "plugins", relative_path)

            # Create target directory
            os.makedirs(os.path.dirname(target_dir), exist_ok=True)

            # Copy the static directory
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)

            shutil.copytree(source_dir, target_dir, ignore=shutil.ignore_patterns("node_modules/.bin"))

            log.info(f"Staged visualization assets for {viz_id}: {relative_path}")

            return {
                "visualization_id": viz_id,
                "source_path": source_dir,
                "target_path": target_dir,
                "relative_path": relative_path,
                "size": self.get_directory_size(target_dir),
            }

        except Exception as e:
            log.error(f"Failed to stage visualization {viz_id}: {e}")
            if "not found" in str(e).lower():
                raise exceptions.ObjectNotFound(f"Visualization '{viz_id}' not found")
            raise exceptions.InternalServerError(f"Failed to stage visualization: {e}")

    def clean_staged_assets(self) -> Dict:
        """
        Clean all staged visualization assets from static/plugins/visualizations.
        This is equivalent to the gulp cleanPlugins task.
        """
        try:
            static_viz_dir = os.path.join(self.app.config.root, "static", "plugins", "visualizations")

            if not os.path.exists(static_viz_dir):
                return {"cleaned_count": 0, "message": "No staged assets to clean"}

            # Count items before deletion
            items = os.listdir(static_viz_dir)
            item_count = len(items)

            # Remove all contents
            shutil.rmtree(static_viz_dir)

            # Recreate empty directory
            os.makedirs(static_viz_dir, exist_ok=True)

            log.info(f"Cleaned {item_count} staged visualization assets")

            return {"cleaned_count": item_count, "cleaned_items": items}

        except Exception as e:
            log.error(f"Failed to clean staged assets: {e}")
            raise exceptions.InternalServerError(f"Failed to clean staged assets: {e}")

    def get_staging_status(self) -> Dict:
        """
        Get information about currently staged visualizations.
        """
        try:
            static_viz_dir = os.path.join(self.app.config.root, "static", "plugins", "visualizations")

            if not os.path.exists(static_viz_dir):
                return {"staged_count": 0, "staged_visualizations": [], "total_size": 0}

            staged_items = []
            total_size = 0

            for item in os.listdir(static_viz_dir):
                item_path = os.path.join(static_viz_dir, item)
                if os.path.isdir(item_path):
                    size = self.get_directory_size(item_path)
                    total_size += size

                    staged_items.append(
                        {"name": item, "path": item_path, "size": size, "last_modified": os.path.getmtime(item_path)}
                    )

            return {"staged_count": len(staged_items), "staged_visualizations": staged_items, "total_size": total_size}

        except Exception as e:
            log.error(f"Failed to get staging status: {e}")
            raise exceptions.InternalServerError(f"Failed to get staging status: {e}")

    def _extract_viz_name_from_path(self, relative_path: str) -> Optional[str]:
        """Extract visualization name from a relative path like 'visualizations/circster/static'."""
        parts = relative_path.split(os.sep)
        if len(parts) >= 3 and parts[0] == "visualizations" and parts[-1] == "static":
            if len(parts) == 3:
                # Simple case: visualizations/circster/static
                return parts[1]
            elif len(parts) == 4:
                # Nested case: visualizations/jqplot/jqplot_bar/static
                return f"{parts[1]}/{parts[2]}"
        return None
