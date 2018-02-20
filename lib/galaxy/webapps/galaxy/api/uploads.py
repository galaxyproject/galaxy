"""
API operations for uploaded files in storage.
"""
import hashlib
import logging
import os
import time

from galaxy import exceptions
from galaxy.web import expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class UploadsAPIController(BaseAPIController):

    @expose_api_anonymous
    def index(self, trans, **kwd):
        raise exceptions.NotImplemented("Listing uploads is not implemented.")

    @expose_api_anonymous
    def create(self, trans, **kwd):
        """
        GET /api/remote_files/

        Displays remote files.

        :param  target:      target to load available datasets from, defaults to ftp
            possible values: ftp, userdir, importdir
        :type   target:      str

        :param  format:      requested format of data, defaults to flat
            possible values: flat, jstree, ajax

        :returns:   list of available files
        :rtype:     list
        """
        print(kwd)
        return {}
