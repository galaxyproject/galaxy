import logging
import os

from galaxy import web
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.util.path import (
    join,
    safe_contains,
)
from galaxy.webapps.base.controller import BaseUIController

log = logging.getLogger(__name__)


def _asset_exists_and_is_safe(repo_path, asset_path):
    if not safe_contains(repo_path, asset_path):
        raise RequestParameterInvalidException()
    return os.path.exists(asset_path)


class ShedToolStatic(BaseUIController):
    @web.expose
    def index(self, trans, shed, owner, repo, tool, version, image_file):
        """
        Open an image file that is contained in an installed tool shed repository or that is referenced by a URL for display.  The
        image can be defined in either a README.rst file contained in the repository or the help section of a Galaxy tool config that
        is contained in the repository.  The following image definitions are all supported.  The former $PATH_TO_IMAGES is no longer
        required, and is now ignored.
        .. image:: https://raw.github.com/galaxy/some_image.png
        .. image:: $PATH_TO_IMAGES/some_image.png
        .. image:: /static/images/some_image.gif
        .. image:: some_image.jpg
        .. image:: /deep/some_image.png
        """
        guid = "/".join((shed, "repos", owner, repo, tool, version))
        tool = trans.app.toolbox.get_tool(guid)
        repo_path = os.path.abspath(tool._repository_dir)
        found_path = None

        if "static/images" not in image_file:
            asset_path = os.path.abspath(join(repo_path, "static", "images", image_file))
            if _asset_exists_and_is_safe(repo_path, asset_path):
                found_path = asset_path

        if not found_path:
            asset_path = os.path.abspath(join(repo_path, image_file))
            if _asset_exists_and_is_safe(repo_path, asset_path):
                found_path = asset_path

        if found_path:
            ext = os.path.splitext(image_file)[-1].lstrip(".")
            if ext:
                mime = trans.app.datatypes_registry.get_mimetype_by_extension(ext)
                if mime:
                    trans.response.set_content_type(mime)
            return open(found_path, "rb")
        else:
            raise RequestParameterInvalidException()
