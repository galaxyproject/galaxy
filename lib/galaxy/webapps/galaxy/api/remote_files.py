"""
API operations on remote files.
"""
import hashlib
import logging
from operator import itemgetter

from galaxy import exceptions
from galaxy.files import ProvidesUserFileSourcesUserContext
from galaxy.util import (
    jstree,
    smart_str,
)
from galaxy.web import expose_api
from galaxy.webapps.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class RemoteFilesAPIController(BaseAPIController):

    @expose_api
    def index(self, trans, **kwd):
        """
        GET /api/remote_files/

        Displays remote files.

        :param  target:      target to load available datasets from, defaults to ftpdir
            possible values: ftpdir, userdir, importdir
        :type   target:      str

        :param  format:      requested format of data, defaults to flat
            possible values: flat, jstree

        :returns:   list of available files
        :rtype:     list
        """
        # If set, target must be one of 'ftpdir' (default), 'userdir', 'importdir'
        target = kwd.get('target', 'ftpdir')

        user_context = ProvidesUserFileSourcesUserContext(trans)
        default_recursive = False
        default_format = "uri"

        if "://" in target:
            uri = target
        elif target == 'userdir':
            uri = "gxuserimport://"
            default_format = "flat"
            default_recursive = True
        elif target == 'importdir':
            uri = 'gximport://'
            default_format = "flat"
            default_recursive = True
        elif target in ['ftpdir', 'ftp']:  # legacy, allow both
            uri = 'gxftp://'
            default_format = "flat"
            default_recursive = True
        else:
            raise exceptions.RequestParameterInvalidException("Invalid target parameter supplied [%s]" % target)

        format = kwd.get('format', default_format)
        recursive = kwd.get('recursive', default_recursive)

        file_sources = self.app.file_sources
        file_sources.validate_uri_root(uri, user_context=user_context)

        file_source_path = file_sources.get_file_source_path(uri)
        file_source = file_source_path.file_source
        index = file_source.list(file_source_path.path, recursive=recursive, user_context=user_context)
        if format == "flat":
            # rip out directories, ensure sorted by path
            index = [i for i in index if i["class"] == "File"]
            index = sorted(index, key=itemgetter("path"))
        if format == "jstree":
            disable = kwd.get('disable', 'folders')

            jstree_paths = []
            for ent in index:
                path = ent["path"]
                path_hash = hashlib.sha1(smart_str(path)).hexdigest()
                if ent["class"] == "Directory":
                    path_type = 'folder'
                    disabled = True if disable == 'folders' else False
                else:
                    path_type = 'file'
                    disabled = True if disable == 'files' else False

                jstree_paths.append(jstree.Path(path, path_hash, {'type': path_type, 'state': {'disabled': disabled}, 'li_attr': {'full_path': path}}))
            userdir_jstree = jstree.JSTree(jstree_paths)
            index = userdir_jstree.jsonData()

        return index

    @expose_api
    def plugins(self, trans, **kwd):
        """
        GET /api/remote_files/plugins

        Display plugin information for each of the gxfiles:// URI targets available.

        :returns:   list of configured plugins
        :rtype:     list
        """
        return self.app.file_sources.plugins_to_dict()
