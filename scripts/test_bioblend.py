"""Start the workspace Galaxy server and run BioBlend's tox suite against it."""

import os
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml


def main():
    root = Path(__file__).resolve().parents[1]
    bioblend = Path(sys.argv[1]).resolve()
    tox_env = sys.argv[2]
    with tempfile.TemporaryDirectory(prefix="galaxy-bioblend-") as directory:
        config_dir = Path(directory)
        master_key = secrets.token_hex(16)
        user_email = "bioblend@localhost.localdomain"
        shed_conf = config_dir / "shed_tool_conf.xml"
        shed_conf.write_text(f'<toolbox tool_path="{config_dir / "shed_tools"}"/>')
        config = {
            "gravity": {"galaxy_root": str(root), "gunicorn": {"bind": "localhost:8080"}},
            "galaxy": {
                "managed_config_dir": str(config_dir / "config"),
                "data_dir": str(config_dir / "database"),
                "database_connection": os.environ["DATABASE_CONNECTION"],
                "tool_config_file": ",".join(
                    str(path)
                    for path in (
                        root / "config/tool_conf.xml.sample",
                        shed_conf,
                        root / "test/functional/tools/sample_tool_conf.xml",
                    )
                ),
                "tool_dependency_dir": str(root / "database/dependencies"),
                "allow_path_paste": True,
                "admin_users": user_email,
                "allow_user_deletion": True,
                "enable_beta_workflow_modules": True,
                "enable_beta_tool_formats": True,
                "master_api_key": master_key,
                "enable_quotas": True,
                "cleanup_job": "onsuccess",
                "enable_celery_tasks": True,
                "vault_config_file": str(bioblend / "tests/template_vault_conf.yml"),
            },
        }
        config_file = config_dir / "galaxy.yml"
        config_file.write_text(yaml.safe_dump(config))
        env = dict(
            os.environ,
            GALAXY_CONFIG_FILE=str(config_file),
            GRAVITY_STATE_DIR=str(config_dir / "gravity"),
            GALAXY_SKIP_CLIENT_BUILD="1",
            BIOBLEND_GALAXY_MASTER_API_KEY=master_key,
            BIOBLEND_GALAXY_USER_EMAIL=user_email,
            BIOBLEND_GALAXY_URL="http://localhost:8080",
        )
        try:
            subprocess.run(["./run.sh", "--daemon"], cwd=root, env=env, check=True)
            deadline = time.monotonic() + 120
            while True:
                try:
                    with urllib.request.urlopen("http://localhost:8080/api/version", timeout=5):
                        break
                except (urllib.error.URLError, TimeoutError):
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Galaxy did not become ready within 120 seconds")
                    time.sleep(1)
            subprocess.run(["tox", "-e", tox_env], cwd=bioblend, env=env, check=True)
        finally:
            subprocess.run(["./run.sh", "--daemon", "stop"], cwd=root, env=env, check=False)
            for log in (config_dir / "gravity/log").glob("*.log"):
                print(f"--- {log.name} ---", flush=True)
                print(log.read_text(errors="replace"), flush=True)


if __name__ == "__main__":
    main()
