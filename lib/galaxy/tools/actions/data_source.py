import logging

from . import DefaultToolAction

log = logging.getLogger( __name__ )


class DataSourceToolAction( DefaultToolAction ):
    """Tool action used for Data Source Tools"""

    def _get_default_data_name( self, dataset, tool, on_text=None, trans=None, incoming=None, history=None, params=None, job_params=None, **kwd ):
        if incoming and 'name' in incoming:
            return incoming[ 'name' ]
        return super( DataSourceToolAction, self )._get_default_data_name( dataset, tool, on_text=on_text, trans=trans, incoming=incoming, history=history, params=params, job_params=job_params )
