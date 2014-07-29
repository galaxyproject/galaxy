from datetime import datetime

from sqlalchemy import (
    and_,
    func
)

from galaxy import model

import logging
log = logging.getLogger( __name__ )


class RuleHelper( object ):
    """ Utillity to allow job rules to interface cleanly with the rest of
    Galaxy and shield them from low-level details of models, metrics, etc....

    Currently focus is on figuring out job statistics for a given user, but
    could interface with other stuff as well.
    """

    def __init__( self, app ):
        self.app = app

    def job_count(
        self,
        **kwds
    ):
        query = self.query( model.Job )
        return self._filter_job_query( query, **kwds ).count()

    def sum_job_runtime(
        self,
        **kwds
    ):
        # TODO: Consider sum_core_hours or something that scales runtime by
        # by calculated cores per job.
        query = self.metric_query(
            select=func.sum( model.JobMetricNumeric.table.c.metric_value ),
            metric_name="runtime_seconds",
            plugin="core",
        )
        query = query.join( model.Job )
        return float( self._filter_job_query( query, **kwds ).first()[ 0 ] )

    def metric_query( self, select, metric_name, plugin, numeric=True ):
        metric_class = model.JobMetricNumeric if numeric else model.JobMetricText
        query = self.query( select )
        query = query.filter( metric_class.table.c.plugin == plugin )
        query = query.filter( metric_class.table.c.metric_name == metric_name )
        return query

    def query( self, select_expression ):
        return self.app.model.context.query( select_expression )

    def _filter_job_query(
        self,
        query,
        for_user_email=None,
        for_destination=None,
        for_job_states=None,
        created_in_last=None,
        updated_in_last=None,
    ):
        query = query.join( model.User )
        if for_user_email is not None:
            query = query.filter( model.User.table.c.email == for_user_email )

        if for_destination is not None:
            query = query.filter( model.Job.table.c.destination_id == for_destination )

        if created_in_last is not None:
            end_date = datetime.now()
            start_date = end_date - created_in_last
            query = query.filter( model.Job.table.c.create_time >= start_date )

        if updated_in_last is not None:
            end_date = datetime.now()
            start_date = end_date - updated_in_last
            log.info( end_date )
            log.info( start_date )
            query = query.filter( model.Job.table.c.update_time >= start_date )

        if for_job_states is not None:
            query = query.filter( model.Job.table.c.state.in_( for_job_states ) )

        return query
