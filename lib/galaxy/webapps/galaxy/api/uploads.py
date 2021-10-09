"""
API operations for uploaded files in storage.
"""
import json
import logging
import os
import re

from galaxy import exceptions
from galaxy.web import (
    expose_api_raw_anonymous,
    legacy_expose_api_anonymous,
)
from . import (
    BaseGalaxyAPIController,
)

log = logging.getLogger(__name__)


class UploadsAPIController(BaseGalaxyAPIController):

    READ_CHUNK_SIZE = 2 ** 16

    @expose_api_raw_anonymous
    def tus(self, trans, payload, session_id=None, **kwargs):
        """
        PATCH /api/upload/resumable_upload/{filename}
        """
        if isinstance(payload, str):
            # WSGI middleware
            with open(f"{payload}.info") as info:
                payload = json.load(info)
                metadata = payload['upload_metadata']
                size = payload['upload_length']
        else:
            # tusd server hook
            metadata = payload['Upload']['MetaData']
            session_id = payload['Upload']['ID']
            size = payload['Upload']['Size']
        trans.response.headers['upload-offset'] = size
        filename = metadata.get('filename', 'Uploaded dataset')
        dbkey = metadata.get('dbkey', '?')
        history_id = metadata.get('history_id')
        if not history_id and not trans.session:
            raise exceptions.RequestParameterMissingException("history_id or galaxy session required")
        ext = 'auto'
        for key in ['ext', 'file_type', 'extension']:
            if key in metadata:
                ext = metadata[key]
                break
        _create = trans.webapp.api_controllers['tools']._create
        inputs = {
            "file_count": 1,
            "dbkey": dbkey,
            "file_type": "auto",
            "files_0|type": "upload_dataset",
            "files_0|NAME": filename,
            "files_0|to_posix_lines": "Yes",
            "files_0|dbkey": dbkey,
            "files_0|file_type": ext,
            "files_0|file_data": {"session_id": session_id, "name": filename}}
        tool_payload = {'tool_id': 'upload1', 'inputs': inputs, 'history_id': history_id}
        _create(trans, tool_payload)
        trans.response.status = 204

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
        if re.match(r'^[\w-]+$', session_id) is None:
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
