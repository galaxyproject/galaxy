"""
Provides web interaction with RealTimeTools
"""
import logging

from galaxy import (
    model,
    web
)
from galaxy.web import url_for
from galaxy.web.base.controller import (
    BaseUIController,
)

from galaxy.web.framework.helpers import (
    grids,
    time_ago,
)

log = logging.getLogger(__name__)


class RealTimeToolEntryPointListGrid(grids.Grid):
    def get_url_args(item):
        """
        Returns dictionary used to create item link.
        """
        url_kwargs = dict(controller="realtime", action="access_entry_point_ri", entry_point_id=item.id)
        return url_kwargs

    use_panels = True
    title = "Available RealTimeTools"
    model_class = model.RealTimeToolEntryPoint
    default_filter = {"name": "All"}
    default_sort_key = "-update_time"
    columns = [
        grids.TextColumn("Name", key="name", filterable="advanced", link=get_url_args),
        grids.GridColumn("Active", key="active"),
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
        grids.GridOperation("Open", condition=(lambda item: item.active), async_compatible=False),
        grids.GridOperation("Stop", condition=(lambda item: item.active), async_compatible=False),
    ]

    def build_initial_query(self, trans, **kwargs):
        # Get list of user's active RealTimeTools
        return trans.app.realtime_manager.get_nonterminal_for_user_by_trans(trans)


class RealTime(BaseUIController):
    _rtt_ep_grid = RealTimeToolEntryPointListGrid()

    @web.expose
    def index(self, trans, realtime_id=None, **kwd):
        realtime = None
        if realtime_id:
            realtime_id = self.decode_id(realtime_id)
            realtime = trans.sa_session.query(trans.app.model.RealTimeTool).get(realtime_id)
        if realtime:
            if trans.app.realtime_manager.can_access_realtime(trans, realtime):
                if realtime.entry_points:
                    if len(realtime.entry_points) == 1:
                        return self.access_entry_point(trans, entry_point_id=trans.security.encode_id(realtime.entry_points[0].id))
                    else:
                        return trans.response.send_redirect(url_for(controller="realtime", action="list"))
            else:
                return trans.show_error_message('Access not authorized.')
        return trans.show_error_message('RealTimeTool instance not found')

    @web.expose
    def access_entry_point_ri(self, trans, entry_point_id=None):
        return trans.response.send_redirect(url_for(controller='realtime', action='access_entry_point', entry_point_id=trans.security.encode_id(entry_point_id)))

    @web.expose
    def access_entry_point(self, trans, entry_point_id=None):
        if entry_point_id:
            entry_point_id = self.decode_id(entry_point_id)
            entry_point = trans.sa_session.query(trans.app.model.RealTimeToolEntryPoint).get(entry_point_id)
            if trans.app.realtime_manager.can_access_entry_point(trans, entry_point):
                if entry_point.realtime.active and entry_point.configured:
                    rval = (url_for('%s/%s/%s/%s/' % (trans.app.config.realtime_prefix, entry_point.__class__.__name__, trans.security.encode_id(entry_point.id), entry_point.token)))
                    if entry_point.entry_url:
                        rval = '%s%s' % (rval, entry_point.entry_url)
                    return trans.response.send_redirect(rval)
                else:
                    return trans.show_error_message('RealTimeTool is not active. If you recently launched this tool it may not be ready yet, please wait a moment and refresh this page.')
        return trans.show_error_message('Access not authorized.')

    def _get_job_for_dataset(self, trans, dataset_id):
        '''
        Return the job for the given dataset. This will throw an error if the
        dataset is either nonexistent or inaccessible to the user.
        '''
        hda = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get(self.decode_id(dataset_id))
        return hda.creating_job

    def _get_job(self, trans, job_id):
        '''
        Return the job for the given dataset. This will throw an error if the
        dataset is either nonexistent or inaccessible to the user.
        '''
        return trans.sa_session.query(trans.app.model.Job).get(self.decode_id(job_id))

    @web.expose_api
    def list(self, trans, **kwargs):
        """List all available realtimetools"""
        return self._rtt_ep_grid(trans)
        rtts = trans.app.realtime_manager.get_nonterminal_for_user_by_trans(trans)
        eps = []
        if rtts:
            for rtt in rtts:
                for ep in rtt.entry_points:
                    eps.append(self.encode_all_ids(trans, ep.to_dict(), True))
        return self._rtt_ep_grid(eps)

    @web.expose_api
    def stop(self, trans, realtime_id=None, realtime_entry_id=None):
        """List all available realtimetools"""
        if realtime_id:
            realtime = trans.app.model.RealTimeTool.get(trans.security.decode_id(realtime_id))
        elif realtime_entry_id:
            realtime = trans.app.model.RealTimeToolEntryPoint.get(trans.security.decode_id(realtime_entry_id)).realtime
        else:
            return dict(message="Can't stop: RealTimeTool not provided.", state='error')
        stopped = trans.app.realtime_manager.stop(realtime)
        if stopped:
            return dict(message="RealTimeTool has been stopped", state='ok')
        return dict(message="Unable to stop RealTimeTool", state='error')
