# We put a tool that references this package into the tool shed
# so we have to provide this legacy location for import indefinitely
# it seems.
from galaxy.util.ucsc import UCSCLimitException, UCSCOutWrapper

__all__ = ('UCSCOutWrapper', 'UCSCLimitException')
