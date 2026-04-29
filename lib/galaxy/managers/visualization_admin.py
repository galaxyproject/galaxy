"""Manager for visualization package administration."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from glob import glob

import requests
import yaml

from galaxy import exceptions
from galaxy.structured_app import MinimalManagerApp
from galaxy.util.path import safe_relpath

log = logging.getLogger(__name__)

_NPM_PACKAGE_RE = re.compile(r"^(@[a-z0-9][a-z0-9._~-]*/)?[a-z0-9][a-z0-9._~-]*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+([a-zA-Z0-9.+-]*)$")
_VIZ_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+(/[a-zA-Z0-9_-]+)?$")


class VisualizationPackageManager:
    """Manager for visualization package operations."""

    def __init__(self, app: MinimalManagerApp):
        self.app = app
        self.config_path = os.path.join(app.config.root, "config", "visualization_packages.yml")
        self.package_store_path = os.path.join(app.config.root, "config", "visualization_packages")
        self.static_path = os.path.join(app.config.root, "static", "plugins", "visualizations")
        self.legacy_visualizations_path = os.path.join(app.config.root, "config", "plugins", "visualizations")

        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        os.makedirs(self.package_store_path, exist_ok=True)
        os.makedirs(self.static_path, exist_ok=True)

    @staticmethod
    def validate_npm_inputs(package: str, version: str) -> None:
        """Reject package names or versions that could be unsafe to pass to npm."""
        if not _NPM_PACKAGE_RE.match(package):
            raise exceptions.RequestParameterInvalidException(f"Invalid npm package name: {package}")
        if not _SEMVER_RE.match(version):
            raise exceptions.RequestParameterInvalidException(f"Invalid package version (expected semver): {version}")

    @staticmethod
    def validate_viz_id(viz_id: str) -> None:
        """Reject viz IDs that could escape the static directory."""
        if not viz_id or not _VIZ_ID_RE.match(viz_id) or ".." in viz_id:
            raise exceptions.RequestParameterInvalidException(f"Invalid visualization ID: {viz_id}")

    def load_config(self) -> dict:
        """Load and normalize the visualization packages config file.

        Legacy entries that are bare strings get normalized to dict format
        so callers don't need to handle both shapes.
        """
        try:
            if not os.path.exists(self.config_path):
                return {}
            with open(self.config_path) as f:
                raw = yaml.safe_load(f) or {}
            for viz_id, info in raw.items():
                if not isinstance(info, dict):
                    raw[viz_id] = {
                        "package": str(info),
                        "version": "unknown",
                        "enabled": True,
                    }
            return raw
        except Exception as e:
            log.error(f"Failed to load visualization config: {e}")
            raise exceptions.InternalServerError(f"Failed to load configuration: {e}")

    def save_config(self, config: dict) -> None:
        """Save the visualization packages configuration file."""
        try:
            with open(self.config_path, "w") as f:
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=True)
        except Exception as e:
            log.error(f"Failed to save visualization config: {e}")
            raise exceptions.InternalServerError(f"Failed to save configuration: {e}")

    def get_package_info(self, viz_id: str) -> dict | None:
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
            config[viz_id] = {"package": config[viz_id], "enabled": enabled}

        self.save_config(config)

    def install_npm_package(self, package: str, version: str, target_dir: str) -> dict:
        """Install an npm package to a target directory."""
        self.validate_npm_inputs(package, version)
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                package_spec = f"{package}@{version}"
                cmd = [
                    "npm",
                    "install",
                    package_spec,
                    "--prefix",
                    temp_dir,
                    "--no-audit",
                    "--no-fund",
                    "--production",
                ]

                log.info(f"Installing npm package: {package_spec}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=temp_dir)

                if result.returncode != 0:
                    log.error(f"npm install failed: {result.stderr}")
                    raise exceptions.InternalServerError(f"Package installation failed: {result.stderr}")

                # Scoped packages live under node_modules/@scope/name
                if package.startswith("@"):
                    source_path = os.path.join(temp_dir, "node_modules", *package.split("/"))
                else:
                    source_path = os.path.join(temp_dir, "node_modules", package)

                if not os.path.exists(source_path):
                    raise exceptions.InternalServerError(
                        f"Package directory not found after installation: {source_path}"
                    )

                os.makedirs(target_dir, exist_ok=True)
                shutil.copytree(source_path, target_dir, dirs_exist_ok=True)
                self.validate_package_structure(target_dir)

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
        except (
            exceptions.InternalServerError,
            exceptions.RequestParameterInvalidException,
        ):
            raise
        except Exception as e:
            log.error(f"Failed to install npm package {package}@{version}: {e}")
            raise exceptions.InternalServerError(f"Package installation failed: {e}")

    def validate_package_structure(self, package_dir: str) -> bool:
        """Validate that a package has the minimum required structure."""
        package_json_path = os.path.join(package_dir, "package.json")
        if not os.path.exists(package_json_path):
            raise exceptions.ConfigurationError("Required file missing: package.json")

        try:
            with open(package_json_path) as f:
                package_json = json.load(f)
            for field in ("name", "version"):
                if field not in package_json:
                    raise exceptions.ConfigurationError(f"package.json missing required field: {field}")
        except json.JSONDecodeError as e:
            raise exceptions.ConfigurationError(f"Invalid package.json: {e}")

        return True

    def cleanup_package_files(self, viz_id: str) -> None:
        """Remove both managed package files and staged assets for a visualization."""
        for path in (self.get_package_path(viz_id), self.get_staged_path(viz_id)):
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                except Exception as e:
                    log.error(f"Failed to cleanup files for {viz_id}: {e}")
                    raise exceptions.InternalServerError(f"Failed to cleanup package files: {e}")
        log.info(f"Cleaned up package files for {viz_id}")

    def get_package_path(self, viz_id: str) -> str:
        """Get the managed filesystem path for an installed runtime package."""
        return os.path.join(self.package_store_path, viz_id)

    def get_staged_path(self, viz_id: str) -> str:
        """Get the served static filesystem path for a staged visualization."""
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

    def get_package_metadata(self, viz_id: str) -> dict:
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

    def query_npm_registry(self, search_term: str | None = None) -> list[dict]:
        """Query npm registry for @galaxyproject visualization packages."""
        try:
            base_url = "https://registry.npmjs.org/-/search"
            query_parts = ["scope:galaxyproject"]
            if search_term:
                query_parts.append(search_term)

            params: dict[str, str | int] = {
                "text": " ".join(query_parts),
                "size": 250,
            }

            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            packages = []

            for result in data.get("objects", []):
                package_info = result.get("package", {})
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

    def get_package_versions(self, package_name: str) -> list[str]:
        """Get available versions for a specific package from npm registry."""
        try:
            url = f"https://registry.npmjs.org/{package_name}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            versions = list(data.get("versions", {}).keys())
            versions.sort(reverse=True)
            return versions

        except requests.RequestException as e:
            log.error(f"Failed to get versions for {package_name}: {e}")
            raise exceptions.InternalServerError(f"Failed to get package versions: {e}")

    def backup_config(self) -> str | None:
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
        if not os.path.exists(backup_path):
            raise exceptions.ObjectNotFound("Backup file not found")
        try:
            shutil.copy2(backup_path, self.config_path)
            log.info("Configuration restored from backup")
        except Exception as e:
            log.error(f"Failed to restore config: {e}")
            raise exceptions.InternalServerError(f"Failed to restore configuration: {e}")

    def stage_all_visualizations(self) -> dict:
        """Stage all visualization assets from managed and legacy sources to static/plugins."""
        try:
            staged_count = 0
            staged_visualizations = []
            errors = []
            seen_viz_ids = set()

            for stage_spec in self._iter_stage_specs():
                try:
                    self._stage_spec(stage_spec)
                    staged_count += 1
                    if stage_spec["viz_id"] not in seen_viz_ids:
                        staged_visualizations.append(stage_spec["viz_id"])
                        seen_viz_ids.add(stage_spec["viz_id"])
                except Exception as e:
                    error_msg = f"Failed to stage {stage_spec['source_path']}: {e}"
                    log.error(error_msg)
                    errors.append(error_msg)

            return {
                "staged_count": staged_count,
                "staged_visualizations": staged_visualizations,
                "errors": errors,
            }

        except Exception as e:
            log.error(f"Failed to stage visualizations: {e}")
            raise exceptions.InternalServerError(f"Failed to stage visualizations: {e}")

    def stage_visualization(self, viz_id: str) -> dict:
        """Stage assets for a specific visualization from managed or legacy sources."""
        try:
            stage_spec = self._get_stage_spec(viz_id)
            self._stage_spec(stage_spec)
            return {
                "visualization_id": viz_id,
                "source_path": stage_spec["source_path"],
                "target_path": stage_spec["target_path"],
                "relative_path": stage_spec["relative_path"],
                "size": self.get_directory_size(stage_spec["target_path"]),
            }

        except exceptions.ObjectNotFound:
            raise
        except Exception as e:
            log.error(f"Failed to stage visualization {viz_id}: {e}")
            raise exceptions.InternalServerError(f"Failed to stage visualization: {e}")

    def clean_staged_assets(self) -> dict:
        """Clean all staged visualization assets from static/plugins/visualizations."""
        try:
            static_viz_dir = os.path.join(self.app.config.root, "static", "plugins", "visualizations")

            if not os.path.exists(static_viz_dir):
                return {"cleaned_count": 0, "message": "No staged assets to clean"}

            items = os.listdir(static_viz_dir)
            item_count = len(items)
            shutil.rmtree(static_viz_dir)
            os.makedirs(static_viz_dir, exist_ok=True)

            log.info(f"Cleaned {item_count} staged visualization assets")
            return {"cleaned_count": item_count, "cleaned_items": items}

        except Exception as e:
            log.error(f"Failed to clean staged assets: {e}")
            raise exceptions.InternalServerError(f"Failed to clean staged assets: {e}")

    def get_staging_status(self) -> dict:
        """Get information about currently staged visualizations."""
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
                        {
                            "name": item,
                            "path": item_path,
                            "size": size,
                            "last_modified": os.path.getmtime(item_path),
                        }
                    )

            return {
                "staged_count": len(staged_items),
                "staged_visualizations": staged_items,
                "total_size": total_size,
            }

        except Exception as e:
            log.error(f"Failed to get staging status: {e}")
            raise exceptions.InternalServerError(f"Failed to get staging status: {e}")

    def _extract_viz_name_from_path(self, relative_path: str) -> str | None:
        """Extract visualization name from a relative path like 'visualizations/circster/static'."""
        parts = relative_path.split(os.sep)
        if len(parts) >= 3 and parts[0] == "visualizations" and parts[-1] == "static":
            if len(parts) == 3:
                return parts[1]
            elif len(parts) == 4:
                return f"{parts[1]}/{parts[2]}"
        return None

    def _iter_stage_specs(self) -> list[dict]:
        specs = []
        managed_viz_ids = set()

        config = self.load_config()
        for viz_id in sorted(config):
            package_path = self.get_package_path(viz_id)
            if os.path.isdir(package_path):
                specs.append(self._build_managed_stage_spec(viz_id, package_path))
                managed_viz_ids.add(viz_id)

        source_patterns = [
            os.path.join(self.legacy_visualizations_path, "*", "static"),
            os.path.join(self.legacy_visualizations_path, "*", "*", "static"),
        ]
        for pattern in source_patterns:
            for source_dir in sorted(glob(pattern)):
                if "node_modules/.bin" in source_dir:
                    continue
                relative_path = os.path.relpath(source_dir, os.path.join(self.app.config.root, "config", "plugins"))
                viz_name = self._extract_viz_name_from_path(relative_path)
                if not viz_name or viz_name in managed_viz_ids:
                    continue
                specs.append(self._build_legacy_stage_spec(viz_name, source_dir))

        return specs

    def _get_stage_spec(self, viz_id: str) -> dict:
        package_path = self.get_package_path(viz_id)
        if os.path.isdir(package_path):
            return self._build_managed_stage_spec(viz_id, package_path)

        legacy_paths = [os.path.join(self.legacy_visualizations_path, viz_id, "static")]
        if "/" in viz_id:
            first, second = viz_id.split("/", 1)
            legacy_paths.append(os.path.join(self.legacy_visualizations_path, first, second, "static"))

        for path in legacy_paths:
            if os.path.isdir(path):
                return self._build_legacy_stage_spec(viz_id, path)

        raise exceptions.ObjectNotFound(f"Static assets not found for visualization '{viz_id}'")

    def _build_managed_stage_spec(self, viz_id: str, package_path: str) -> dict:
        plugin_name = viz_id.split("/")[-1]
        config_file = os.path.join(package_path, "static", f"{plugin_name}.xml")
        if not os.path.isfile(config_file):
            raise exceptions.ConfigurationError(
                f"Runtime visualization '{viz_id}' is missing required static config: {config_file}"
            )
        relative_path = os.path.relpath(package_path, self.app.config.root)
        if not safe_relpath(relative_path):
            raise exceptions.InternalServerError(f"Unsafe staging path for visualization '{viz_id}'")
        return {
            "viz_id": viz_id,
            "source_path": package_path,
            "target_path": self.get_staged_path(viz_id),
            "relative_path": relative_path,
        }

    def _build_legacy_stage_spec(self, viz_id: str, source_dir: str) -> dict:
        plugins_base_dir = os.path.join(self.app.config.root, "config", "plugins")
        relative_path = os.path.relpath(source_dir, plugins_base_dir)
        if not safe_relpath(relative_path):
            raise exceptions.InternalServerError(f"Unsafe staging path for visualization '{viz_id}'")
        return {
            "viz_id": viz_id,
            "source_path": source_dir,
            "target_path": os.path.join(self.get_staged_path(viz_id), "static"),
            "relative_path": relative_path,
        }

    def _stage_spec(self, stage_spec: dict) -> None:
        source_path = stage_spec["source_path"]
        target_path = stage_spec["target_path"]

        if not os.path.exists(source_path):
            raise exceptions.ObjectNotFound(f"Static assets not found for visualization '{stage_spec['viz_id']}'")

        if os.path.exists(target_path):
            src_mtime = os.path.getmtime(source_path)
            tgt_mtime = os.path.getmtime(target_path)
            if tgt_mtime >= src_mtime:
                return
            shutil.rmtree(target_path)

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.copytree(
            source_path,
            target_path,
            ignore=shutil.ignore_patterns("node_modules/.bin"),
        )
        log.info(f"Staged visualization assets for {stage_spec['viz_id']}: {stage_spec['relative_path']}")
