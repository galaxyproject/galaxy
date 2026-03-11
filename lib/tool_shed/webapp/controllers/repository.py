import logging
import os

from galaxy import web
from galaxy.webapps.base.controller import BaseUIController
from tool_shed.util import repository_util

log = logging.getLogger(__name__)


class RepositoryController(BaseUIController):

    @web.expose
    def display_image_in_repository(self, trans, **kwd):
        """
        Open an image file that is contained in a repository for display.
        Images can be referenced from README.rst or Galaxy tool help sections.
        """
        repository_id = kwd.get("repository_id", None)
        relative_path_to_image_file = kwd.get("image_file", None)
        if repository_id and relative_path_to_image_file:
            repository = repository_util.get_repository_in_tool_shed(trans.app, repository_id)
            if repository:
                repo_files_dir = repository.repo_path(trans.app)
                path_to_file = repository_util.get_absolute_path_to_file_in_repository(
                    repo_files_dir, relative_path_to_image_file
                )
                if os.path.exists(path_to_file):
                    file_name = os.path.basename(relative_path_to_image_file)
                    try:
                        extension = file_name.split(".")[-1]
                    except Exception:
                        extension = None
                    if extension:
                        mimetype = trans.app.datatypes_registry.get_mimetype_by_extension(extension)
                        if mimetype:
                            trans.response.set_content_type(mimetype)
                    return open(path_to_file, "rb")
