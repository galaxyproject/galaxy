"""
API operations for uploaded files in storage.
"""

import logging

from galaxy.web.framework.decorators import expose_api_anonymous
from . import BaseGalaxyAPIController

log = logging.getLogger(__name__)


class UploadsAPIController(BaseGalaxyAPIController):
    READ_CHUNK_SIZE = 2**16

    @expose_api_anonymous
    def hooks(self, trans, **kwds):
        """
        Exposed as POST /api/upload/hooks and /api/upload/resumable_upload
        """
        # Internal endpoint, only purpose is to authenticate user, but may grow additional functionality in the future
        return None
