"""
Chunk (N number of bytes at M offset to a source's beginning) provider.

Primarily for file sources but usable by any iterator that has both
seek and read( N ).
"""

import base64
import logging
import os

from . import (
    base,
    exceptions,
)

log = logging.getLogger(__name__)


class ChunkDataProvider(base.DataProvider):
    """
    Data provider that yields chunks of data from its file.

    Note: this version does not account for lines and works with Binary datatypes.
    """

    MAX_CHUNK_SIZE = 2**16
    DEFAULT_CHUNK_SIZE = MAX_CHUNK_SIZE
    settings = {"chunk_index": "int", "chunk_size": "int"}

    # TODO: subclass from LimitedOffsetDataProvider?
    # see web/framework/base.iterate_file, util/__init__.file_reader, and datatypes.tabular
    def __init__(self, source, chunk_index=0, chunk_size=DEFAULT_CHUNK_SIZE, **kwargs):
        """
        :param chunk_index: if a source can be divided into N number of
            `chunk_size` sections, this is the index of which section to
            return.
        :param chunk_size:  how large are the desired chunks to return
            (gen. in bytes).
        """
        super().__init__(source, **kwargs)
        self.chunk_size = int(chunk_size)
        self.chunk_pos = int(chunk_index) * self.chunk_size

    def validate_source(self, source):
        """
        Does the given source have both the methods `seek` and `read`?
        :raises InvalidDataProviderSource: if not.
        """
        source = super().validate_source(source)
        if (not hasattr(source, "seek")) or (not hasattr(source, "read")):
            raise exceptions.InvalidDataProviderSource(source)
        return source

    def __iter__(self):
        # not reeeally an iterator per se
        self.__enter__()
        self.source.seek(self.chunk_pos, os.SEEK_SET)
        chunk = self.encode(self.source.read(self.chunk_size))
        yield chunk
        self.__exit__()

    def encode(self, chunk):
        """
        Called on the chunk before returning.

        Overrride to modify, encode, or decode chunks.
        """
        return chunk


class Base64ChunkDataProvider(ChunkDataProvider):
    """
    Data provider that yields chunks of base64 encoded data from its file.
    """

    def encode(self, chunk):
        """
        Return chunks encoded in base 64.
        """
        return base64.b64encode(chunk)
