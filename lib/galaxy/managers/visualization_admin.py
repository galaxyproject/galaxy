"""Manager for visualization package administration."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any

import yaml
from packaging.version import (
    InvalidVersion,
    Version,
)

from galaxy import exceptions
from galaxy.config import GalaxyAppConfiguration
from galaxy.util import requests

log = logging.getLogger(__name__)

_NPM_PACKAGE_RE = re.compile(r"^(@[a-z0-9][a-z0-9._~-]*/)?[a-z0-9][a-z0-9._~-]*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+([a-zA-Z0-9.+-]*)$")
# Flat names only: npm packages are flat, the registry keys plugins by name, and the admin routes take
# a single {viz_id} path segment.
_VIZ_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _version_sort_key(version: str) -> tuple[bool, Version | str]:
    # anything packaging can't parse sorts below every real version
    try:
        return (True, Version(version))
    except InvalidVersion:
        return (False, version)


class VisualizationPackageManager:
    """Manager for visualization package operations."""

    def __init__(self, config: GalaxyAppConfiguration) -> None:
        self.config_path = config.visualization_packages_config_file
        self.package_store_path = config.visualization_packages_dir
        # Directories are created on first install, not here: this runs at startup, and Galaxy has to
        # boot even where managed_config_dir isn't writable and nobody installs packages.

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

    def load_config(self) -> dict[str, Any]:
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

    def save_config(self, config: dict[str, Any]) -> None:
        """Save the visualization packages configuration file."""
        temp_path = None
        try:
            config_dir = os.path.dirname(self.config_path)
            os.makedirs(config_dir, exist_ok=True)
            # every process re-reads this at boot and on reload, so swap in a complete file rather than
            # truncating and rewriting it in place
            with tempfile.NamedTemporaryFile("w", dir=config_dir, suffix=".tmp", delete=False) as f:
                temp_path = f.name
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=True)
            os.replace(temp_path, self.config_path)
        except Exception as e:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            log.error(f"Failed to save visualization config: {e}")
            raise exceptions.InternalServerError(f"Failed to save configuration: {e}")

    def get_package_info(self, viz_id: str) -> dict[str, Any] | None:
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

    def get_enabled_packages(self) -> dict[str, str]:
        """Installed, enabled runtime packages, mapped to their directory in the package store."""
        packages = {}
        for viz_id, info in self.load_config().items():
            package_path = self.get_package_path(viz_id)
            if info.get("enabled", True) and os.path.isdir(package_path):
                packages[viz_id] = package_path
        return packages

    @classmethod
    def visualization_id_for_package(cls, package: str) -> str:
        """The id a package installs under: its unscoped name, as for every bundled visualization."""
        viz_id = package.split("/")[-1]
        try:
            cls.validate_viz_id(viz_id)
        except exceptions.RequestParameterInvalidException:
            raise exceptions.RequestParameterInvalidException(
                f"Package name {package} can't be used as a visualization ID (letters, numbers, hyphens and underscores only)"
            )
        return viz_id

    def install_package(self, package: str, version: str) -> dict[str, Any]:
        """Install a new package into the managed store and record it in the config."""
        self.validate_npm_inputs(package, version)
        viz_id = self.visualization_id_for_package(package)
        if self.get_package_info(viz_id) or self.is_package_installed(viz_id):
            raise exceptions.Conflict(f"Package '{viz_id}' is already installed")

        package_path = self.get_package_path(viz_id)
        try:
            install_result = self.install_npm_package(package, version, package_path)
            self._require_static_config(viz_id, package_path, f"{package}@{version}")
            self.add_package_to_config(viz_id, package, version, enabled=True)
        except Exception:
            # a directory without a config entry can't be reinstalled or uninstalled through the API
            shutil.rmtree(package_path, ignore_errors=True)
            raise
        log.info(f"Successfully installed visualization package {viz_id} ({package}@{version})")
        return {**install_result, "id": viz_id}

    def update_package(self, viz_id: str, version: str) -> dict[str, Any]:
        """Safe update: install new version to temp, swap on success, keep old on failure."""
        self.validate_viz_id(viz_id)
        info = self.get_package_info(viz_id)
        if not info:
            raise exceptions.ObjectNotFound(f"Visualization package '{viz_id}' not found")
        package = info["package"]
        enabled = info.get("enabled", True)
        target_dir = self.get_package_path(viz_id)

        # inside the store, so the swap below is a same-filesystem rename rather than copy-then-delete
        os.makedirs(self.package_store_path, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self.package_store_path, prefix=".update-") as update_dir:
            new_pkg_dir = os.path.join(update_dir, viz_id)
            try:
                install_result = self.install_npm_package(package, version, new_pkg_dir)
            except Exception:
                log.warning(f"Failed to install {package}@{version}, keeping existing version")
                raise
            self._require_static_config(viz_id, new_pkg_dir, f"{package}@{version}")

            backup_dir = os.path.join(update_dir, f"{viz_id}_backup")
            if os.path.exists(target_dir):
                shutil.move(target_dir, backup_dir)

            try:
                shutil.move(new_pkg_dir, target_dir)
            except Exception:
                if os.path.exists(backup_dir):
                    shutil.rmtree(target_dir, ignore_errors=True)
                    shutil.move(backup_dir, target_dir)
                raise

        self.add_package_to_config(viz_id, package, version, enabled=enabled)
        log.info(f"Successfully updated visualization package {viz_id} to version {version}")
        return {**install_result, "enabled": enabled}

    def uninstall_package(self, viz_id: str) -> None:
        self.validate_viz_id(viz_id)
        if not self.get_package_info(viz_id) and not self.is_package_installed(viz_id):
            raise exceptions.ObjectNotFound(f"Package '{viz_id}' not found")
        # files first, so a failed removal leaves the entry in place for the admin to retry
        self.cleanup_package_files(viz_id)
        self.remove_package_from_config(viz_id)
        log.info(f"Successfully uninstalled visualization package {viz_id}")

    def _run_npm_install(self, package_spec: str, prefix: str) -> None:
        """Run ``npm install`` for one package into ``prefix``; the only place npm is invoked."""
        cmd = [
            "npm",
            "install",
            package_spec,
            "--prefix",
            prefix,
            "--no-audit",
            "--no-fund",
            "--omit=dev",
            "--ignore-scripts",
            # keep npm's cache and logs out of the Galaxy user's home, which may not be writable
            "--cache",
            os.path.join(prefix, ".npm-cache"),
        ]
        log.info(f"Installing npm package: {package_spec}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=prefix)
        except FileNotFoundError:
            raise exceptions.InternalServerError(
                "No npm executable found on the Galaxy server's PATH; installing visualization packages needs Node.js and npm"
            )
        if result.returncode != 0:
            log.error(f"npm install failed: {result.stderr}")
            raise exceptions.InternalServerError(f"Package installation failed: {result.stderr}")

    def install_npm_package(self, package: str, version: str, target_dir: str) -> dict[str, Any]:
        """Install an npm package to a target directory."""
        self.validate_npm_inputs(package, version)
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                self._run_npm_install(f"{package}@{version}", temp_dir)

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
                shutil.copytree(source_path, target_dir, symlinks=True, dirs_exist_ok=True)
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
        except exceptions.MessageException:
            raise
        except Exception as e:
            log.error(f"Failed to install npm package {package}@{version}: {e}")
            raise exceptions.InternalServerError(f"Package installation failed: {e}")

    def _require_static_config(self, viz_id: str, package_dir: str, package_spec: str) -> None:
        # Same check the client build applies to bundled visualizations; without it the registry can't load the package.
        if not os.path.isfile(os.path.join(package_dir, "static", f"{viz_id}.xml")):
            raise exceptions.RequestParameterInvalidException(
                f"{package_spec} doesn't include static/{viz_id}.xml, so Galaxy can't load it as the "
                f"'{viz_id}' visualization"
            )

    def validate_package_structure(self, package_dir: str) -> bool:
        """Validate that a package has the minimum required structure."""
        package_json_path = os.path.join(package_dir, "package.json")
        if not os.path.exists(package_json_path):
            raise exceptions.RequestParameterInvalidException("Required file missing: package.json")

        try:
            with open(package_json_path) as f:
                package_json = json.load(f)
            for field in ("name", "version"):
                if field not in package_json:
                    raise exceptions.RequestParameterInvalidException(f"package.json missing required field: {field}")
        except json.JSONDecodeError as e:
            raise exceptions.RequestParameterInvalidException(f"Invalid package.json: {e}")

        return True

    def cleanup_package_files(self, viz_id: str) -> None:
        """Remove a package's files from the managed package store."""
        path = self.get_package_path(viz_id)
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

    def get_package_metadata(self, viz_id: str) -> dict[str, Any]:
        """Get metadata from an installed package's package.json."""
        package_path = self.get_package_path(viz_id)
        package_json_path = os.path.join(package_path, "package.json")

        if not os.path.exists(package_json_path):
            return {}

        try:
            with open(package_json_path) as f:
                metadata: dict[str, Any] = json.load(f)
            return metadata
        except Exception as e:
            log.warning(f"Failed to read package.json for {viz_id}: {e}")
            return {}

    def query_npm_registry(self, search_term: str | None = None) -> list[dict[str, Any]]:
        """Query the npm registry for @galaxyproject packages that might be visualizations."""
        try:
            # v1 search ignores the scope: qualifier, so search for the scope name and filter on it below
            base_url = "https://registry.npmjs.org/-/v1/search"
            query_parts = ["@galaxyproject"]
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
                if not package_info.get("name", "").startswith("@galaxyproject/"):
                    continue
                # Published visualizations mostly carry no keywords, so list the whole scope and let
                # the static XML check at install time decide what's actually a visualization.
                packages.append(
                    {
                        "name": package_info.get("name", ""),
                        "description": package_info.get("description", ""),
                        "version": package_info.get("version", ""),
                        "keywords": package_info.get("keywords", []),
                        "author": package_info.get("author", {}),
                        "maintainers": package_info.get("maintainers", []),
                        "links": package_info.get("links", {}),
                        "date": package_info.get("date", ""),
                        "score": result.get("score", {}),
                    }
                )

            return packages

        except requests.exceptions.RequestException as e:
            log.error(f"Failed to query npm registry: {e}")
            raise exceptions.InternalServerError(f"Failed to query package registry: {e}")

    def get_package_versions(self, package_name: str) -> list[str]:
        """Get available versions for a specific package from npm registry."""
        if not _NPM_PACKAGE_RE.match(package_name):
            raise exceptions.RequestParameterInvalidException(f"Invalid npm package name: {package_name}")
        try:
            url = f"https://registry.npmjs.org/{package_name}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            versions = list(data.get("versions", {}).keys())
            versions.sort(key=_version_sort_key, reverse=True)
            return versions

        except requests.exceptions.RequestException as e:
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
