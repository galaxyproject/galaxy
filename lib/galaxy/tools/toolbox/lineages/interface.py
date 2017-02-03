from abc import (
    ABCMeta,
    abstractmethod
)

import six


@six.add_metaclass(ABCMeta)
class ToolLineage(object):
    """
    """

    @abstractmethod
    def get_versions( self, reverse=False ):
        """ Return an ordered list of lineages (ToolLineageVersion) in this
        chain, from oldest to newest.
        """


class ToolLineageVersion(object):
    """ Represents a single tool in a lineage. If lineage is based
    around GUIDs that somehow encode the version (either using GUID
    or a simple tool id and a version). """

    def __init__(self, id, version):
        self.id = id
        self.version = version

    @staticmethod
    def from_id_and_verion( id, version ):
        assert version is not None
        return ToolLineageVersion( id, version )

    @staticmethod
    def from_guid( guid ):
        return ToolLineageVersion( guid, None )

    @property
    def id_based( self ):
        """ Return True if the lineage is defined by GUIDs (in this
        case the indexer of the tools (i.e. the ToolBox) should ignore
        the tool_version (because it is encoded in the GUID and managed
        externally).
        """
        return self.version is None

    def to_dict(self):
        return dict(
            id=self.id,
            version=self.version,
        )
