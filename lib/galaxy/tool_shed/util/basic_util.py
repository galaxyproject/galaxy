import logging
import os
import shutil

import markupsafe

from galaxy.util import (
    nice_size,
    unicodify,
)

log = logging.getLogger(__name__)

CHUNK_SIZE = 2**20  # 1Mb
INSTALLATION_LOG = "INSTALLATION.log"
# Set no activity timeout to 20 minutes.
NO_OUTPUT_TIMEOUT = 3600.0
MAXDIFFSIZE = 8000
MAX_DISPLAY_SIZE = 32768

DOCKER_IMAGE_TEMPLATE = """
# Galaxy Docker image

FROM bgruening/galaxy-stable

MAINTAINER Bjoern A. Gruning, bjoern.gruening@gmail.com

WORKDIR /galaxy-central

${selected_repositories}

# Mark folders as imported from the host.
VOLUME ["/export/", "/data/", "/var/lib/docker"]

# Expose port 80 (webserver), 21 (FTP server), 8800 (Proxy), 9001 (Galaxy report app)
EXPOSE :80
EXPOSE :21
EXPOSE :8800
EXPOSE :9001

# Autostart script that is invoked during container start
CMD ["/usr/bin/startup"]
"""

SELECTED_REPOSITORIES_TEMPLATE = """
RUN install-repository "--url ${tool_shed_url} -o ${repository_owner} --name ${repository_name}"
"""


def get_file_type_str(changeset_revision, file_type):
    if file_type == "zip":
        file_type_str = f"{changeset_revision}.zip"
    elif file_type == "bz2":
        file_type_str = f"{changeset_revision}.tar.bz2"
    elif file_type == "gz":
        file_type_str = f"{changeset_revision}.tar.gz"
    else:
        file_type_str = ""
    return file_type_str


def move_file(current_dir, source, destination, rename_to=None):
    source_path = os.path.abspath(os.path.join(current_dir, source))
    destination_directory = os.path.join(destination)
    if rename_to is not None:
        destination_path = os.path.join(destination_directory, rename_to)
    else:
        source_file = os.path.basename(source_path)
        destination_path = os.path.join(destination_directory, source_file)
    if not os.path.exists(destination_directory):
        os.makedirs(destination_directory)
    shutil.move(source_path, destination_path)


def remove_dir(dir):
    """Attempt to remove a directory from disk."""
    if dir:
        if os.path.exists(dir):
            try:
                shutil.rmtree(dir)
            except Exception:
                pass


def size_string(raw_text, size=MAX_DISPLAY_SIZE):
    """Return a subset of a string (up to MAX_DISPLAY_SIZE) translated to a safe string for display in a browser."""
    if raw_text and len(raw_text) >= size:
        large_str = (
            f"\nFile contents truncated because file size is larger than maximum viewing size of {nice_size(size)}\n"
        )
        raw_text = f"{raw_text[0:size]}{large_str}"
    return raw_text or ""


def stringify(list):
    if list:
        return ",".join(list)
    return ""


def strip_path(fpath):
    """Attempt to strip the path from a file name."""
    if not fpath:
        return fpath
    try:
        file_path, file_name = os.path.split(fpath)
    except Exception:
        file_name = fpath
    return file_name


def to_html_string(text):
    """Translates the characters in text to an html string"""
    if text:
        try:
            text = unicodify(text)
        except UnicodeDecodeError as e:
            return f"Error decoding string: {str(e)}"
        text = str(markupsafe.escape(text))
        text = text.replace("\n", "<br/>")
        text = text.replace("    ", "&nbsp;&nbsp;&nbsp;&nbsp;")
        text = text.replace(" ", "&nbsp;")
    return text


__all__ = (
    "CHUNK_SIZE",
    "DOCKER_IMAGE_TEMPLATE",
    "get_file_type_str",
    "INSTALLATION_LOG",
    "MAX_DISPLAY_SIZE",
    "MAXDIFFSIZE",
    "NO_OUTPUT_TIMEOUT",
    "move_file",
    "remove_dir",
    "SELECTED_REPOSITORIES_TEMPLATE",
    "size_string",
    "stringify",
    "strip_path",
    "to_html_string",
)
