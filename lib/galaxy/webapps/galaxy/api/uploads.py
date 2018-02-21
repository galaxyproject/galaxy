"""
API operations for uploaded files in storage.
"""
import logging
import os
import re

from galaxy import exceptions
from galaxy.web import expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class UploadsAPIController(BaseAPIController):

    @expose_api_anonymous
    def index(self, trans, **kwd):
        raise exceptions.NotImplemented("Listing uploads is not implemented.")

    @expose_api_anonymous
    def create(self, trans, payload, **kwd):
        """
        POST /api/uploads/
        """
        headers = trans.request.headers.environ
        content_range = headers["HTTP_CONTENT_RANGE"]
        session_id = headers["HTTP_SESSION_ID"]
        if content_range:
            m = re.search("(\d+)-(\d+)\/(\d+)", content_range)
            if m is None or len(m.groups()) != 3:
                raise exceptions.MessageException("Requires content range header [START-END/TOTAL].");
            start = int(m.group(1))
            end = int(m.group(2))
            total = int(m.group(3))
        if session_id is None:
            raise exceptions.MessageException("Requires a session id.")
        target_file = "%s/%s" % (trans.app.config.nginx_upload_store, session_id)
        target_size = 0
        if os.path.exists(target_file):
            target_size = os.path.getsize(target_file)
        if start != target_size:
            raise exceptions.MessageException("Chunk missing. Abort.")
        source = payload.get("file")
        with open(target_file, "a") as f:
            f.write(source.file.read())
            f.close()
        source.file.close()
        return {"message": "Chunk successfully saved."}
