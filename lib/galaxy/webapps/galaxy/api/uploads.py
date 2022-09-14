"""
API operations for uploaded files in storage.
"""
import logging
import os
import re

from galaxy import exceptions
from galaxy.web.framework.decorators import (
    expose_api_raw_anonymous,
    legacy_expose_api_anonymous,
)
from . import BaseGalaxyAPIController

log = logging.getLogger(__name__)


class UploadsAPIController(BaseGalaxyAPIController):

    READ_CHUNK_SIZE = 2**16

    @expose_api_raw_anonymous
    def hooks(self, trans, **kwds):
        """
        Exposed as POST /api/upload/hooks and /api/upload/resumable_upload
        """
        # Internal endpoint, only purpose is to authenticate user, but may grow additional functionality in the future
        return None

    @legacy_expose_api_anonymous
    def index(self, trans, **kwd):
        raise exceptions.NotImplemented("Listing uploads is not implemented.")

    @legacy_expose_api_anonymous
    def create(self, trans, payload, **kwd):
        """
        POST /api/uploads/
        """
        session_id = payload.get("session_id")
        session_start = payload.get("session_start")
        session_chunk = payload.get("session_chunk")
        if re.match(r"^[\w-]+$", session_id) is None:
            raise exceptions.MessageException("Requires a session id.")
        if session_start is None:
            raise exceptions.MessageException("Requires a session start.")
        if not hasattr(session_chunk, "file"):
            raise exceptions.MessageException("Requires a session chunk.")
        target_file = os.path.join(trans.app.config.new_file_path, session_id)
        target_size = 0
        if os.path.exists(target_file):
            target_size = os.path.getsize(target_file)
        if session_start != target_size:
            raise exceptions.MessageException("Incorrect session start.")
        chunk_size = os.fstat(session_chunk.file.fileno()).st_size
        if chunk_size > trans.app.config.chunk_upload_size:
            raise exceptions.MessageException("Invalid chunk size.")
        with open(target_file, "ab") as f:
            while True:
                read_chunk = session_chunk.file.read(self.READ_CHUNK_SIZE)
                if not read_chunk:
                    break
                f.write(read_chunk)
        session_chunk.file.close()
        return {"message": "Successful."}
