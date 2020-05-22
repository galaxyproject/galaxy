"""Utilities to help job and tool code setup jobs."""
import os

from galaxy.util import safe_makedirs


def ensure_configs_directory(work_dir):
    configs_dir = os.path.join(work_dir, "configs")
    if not os.path.exists(configs_dir):
        safe_makedirs(configs_dir)
    return configs_dir
