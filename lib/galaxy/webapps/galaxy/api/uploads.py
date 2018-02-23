"""
API operations for uploaded files in storage.
"""
import logging
import os

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
        session_id = payload.get("session_id")
        session_start = payload.get("session_start")
        if session_id is None:
            raise exceptions.MessageException("Requires a session id.")
        if session_start is None:
            raise exceptions.MessageException("Requires a session start.")
        target_file = "%s/%s" % (trans.app.config.new_file_path, session_id)
        target_size = 0
        if os.path.exists(target_file):
            target_size = os.path.getsize(target_file)
        if session_start != target_size:
            raise exceptions.MessageException("Incorrect session start.")
        source = payload.get("session_chunk")
        with open(target_file, "a") as f:
            f.write(source.file.read())
            f.close()
        source.file.close()
        return {"message": "Successful."}
