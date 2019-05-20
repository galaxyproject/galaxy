"""
Provides web interaction with RealTimeTools
"""
import logging

from galaxy import (
    exceptions,
    model,
    web
)
from galaxy.managers.realtime import RealTimeManager
from galaxy.web import url_for
from galaxy.web.base.controller import (
    BaseUIController,
)
from galaxy.web.framework.helpers import (
    grids,
    time_ago,
)

log = logging.getLogger(__name__)


class JobStatusColumn(grids.StateColumn):
    def get_value(self, trans, grid, item):
        return super(JobStatusColumn, self).get_value(trans, grid, item.job)


class EntryPointLinkColumn(grids.GridColumn):
    def get_value(self, trans, grid, item):
        return '<a class="entry-point-link" entry_point_id="%s">%s</div>' % (trans.security.encode_id(item.id), item.name)


class RealTimeToolEntryPointListGrid(grids.Grid):
    def get_url_args(item):
        """
        Returns dictionary used to create item link.
        """
        url_kwargs = dict(controller="realtime", action="access_entry_point", id=item.id)
        return url_kwargs

    def get_url_args_job(item):
        """
        Returns dictionary used to create item link.
        """
        url_kwargs = dict(controller="api/jobs", action='show', id=item.job.id)
        return url_kwargs

    use_panels = True
    title = "Available RealTimeTools"
    model_class = model.RealTimeToolEntryPoint
    default_filter = {"name": "All"}
    default_sort_key = "-update_time"
    columns = [
        EntryPointLinkColumn("Name", filterable="advanced"),
        grids.GridColumn("Active", key="active"),
        JobStatusColumn("Job Info", key="job_state", model_class=model.Job),
        grids.GridColumn("Created", key="created_time", format=time_ago),
        grids.GridColumn("Last Updated", key="modified_time", format=time_ago),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search",
            cols_to_filter=[columns[0]],
            key="free-text-search", visible=False, filterable="standard"
        )
    )
    operations = [
        grids.GridOperation("Stop", condition=(lambda item: item.active), async_compatible=False),
    ]

    def build_initial_query(self, trans, **kwargs):
        # Get list of user's active RealTimeTools
        return trans.app.realtime_manager.get_nonterminal_for_user_by_trans(trans)


class RealTime(BaseUIController):
    entry_point_grid = RealTimeToolEntryPointListGrid()

    @web.expose
    def index(self, trans, job_id=None, **kwd):
        job = trans.sa_session.query(trans.app.model.Job).get(self.decode_id(job_id))
        eps = job.realtimetool_entry_points
        try:
            if eps and len(eps) == 1:
                redirect_target = RealTimeManager(self.app).access_entry_point_target(trans, eps[0].id)
            else:
                redirect_target = url_for(controller="realtime", action="list")
            return trans.response.send_redirect(redirect_target)
        except exceptions.MessageException as e:
            return trans.show_error_message(str(e))

    @web.expose_api_anonymous
    def list(self, trans, **kwargs):
        """List all available realtimetools"""
        operation = kwargs.get('operation', None)
        message = None
        status = None
        if operation:
            eps = []
            ids = kwargs.get('id', None)
            if ids:
                if not isinstance(ids, list):
                    ids = [ids]
                for entry_point_id in ids:
                    entry_point_id = self.decode_id(entry_point_id)
                    entry_point = trans.sa_session.query(trans.app.model.RealTimeToolEntryPoint).get(entry_point_id)
                    if trans.app.realtime_manager.can_access_entry_point(trans, entry_point):
                        eps.append(entry_point)
            if eps:
                failed = []
                succeeded = []
                jobs = []
                if operation == 'stop':
                    for ep in eps:
                        if ep.job not in jobs:
                            stopped = trans.app.realtime_manager.stop(trans, ep)
                            if stopped:
                                succeeded.append(ep)
                                jobs.append(ep.job)
                            else:
                                failed.append(ep)
                        else:
                            succeeded.append(ep)
                    if failed:
                        message = 'Unable to stop %i RealTimeTools.' % (len(failed))
                        status = 'error'
                    if succeeded:
                        message = 'Stopped %i RealTimeTools.' % (len(succeeded))
                        status = 'ok'
        if message and status:
            kwargs['message'] = message
            kwargs['status'] = status
        return self.entry_point_grid(trans, **kwargs)
