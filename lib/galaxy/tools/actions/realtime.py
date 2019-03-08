import logging

from . import DefaultToolAction

log = logging.getLogger(__name__)


class RealTimeToolAction(DefaultToolAction):
    """Tool action used for RealTime Tools"""

    def execute(self, tool, trans, **kwds):
        rval = super(RealTimeToolAction, self).execute(tool, trans, **kwds)
        job, output_dict = rval
        trans.app.realtime_manager.create_realtime(trans, job, tool)
        return rval
