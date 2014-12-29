from abc import ABCMeta
from abc import abstractmethod


class ToolLineage(object):
    """
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_version_ids( self, reverse=False ):
        """ Return an ordered list of lineages in this chain, from
        oldest to newest.
        """
