"""
API operations for asynchonous mode.
"""
import logging

import requests
from six.moves.urllib.parse import urlencode

from galaxy import jobs
from galaxy.util import (
    Params,
    unicodify,
)
from galaxy.util.hash_util import hmac_new
from galaxy.web import (
    expose_api
)
from galaxy.web.base.controller import (
    BaseAPIController
)

log = logging.getLogger(__name__)


class AsyncController(BaseAPIController):

    def __init__(self, app):
        super(AsyncController, self).__init__(app)

    @expose_api
    def default(self, trans, tool_id=None, data_id=None, data_secret=None, **kwd):
        """Catches the tool id and redirects as needed"""
        return self.index(trans, tool_id=tool_id, data_id=data_id, data_secret=data_secret, **kwd)

    @expose_api
    def index(self, trans, tool_id=None, data_secret=None, **kwd):
        """Manages asynchronous connections"""

        if tool_id is None:
            return "tool_id argument is required"
        tool_id = str(tool_id)

        # redirect to main when getting no parameters
        if not kwd:
            return trans.response.send_redirect("/index")

        params = Params(kwd, sanitize=False)
        STATUS = params.STATUS
        URL = params.URL
        data_id = params.data_id

        log.debug('async dataid -> %s' % data_id)
        trans.log_event('Async dataid -> %s' % str(data_id))

        # initialize the tool
        toolbox = self.get_toolbox()
        tool = toolbox.get_tool(tool_id)
        if not tool:
            return "Tool with id %s not found" % tool_id

        #
        # we have an incoming data_id
        #
        if data_id:
            if not URL:
                return "No URL parameter was submitted for data %s" % data_id
            data = trans.sa_session.query(trans.model.HistoryDatasetAssociation).get(data_id)

            if not data:
                return "Data %s does not exist or has already been deleted" % data_id

            if STATUS == 'OK':
                key = hmac_new(trans.app.config.tool_secret, "%d:%d" % (data.id, data.history_id))
                if key != data_secret:
                    return "You do not have permission to alter data %s." % data_id
                # push the job into the queue
                data.state = data.blurb = data.states.RUNNING
                log.debug('executing tool %s' % tool.id)
                trans.log_event('Async executing tool %s' % tool.id, tool_id=tool.id)
                galaxy_url = trans.request.base + '/async/%s/%s/%s' % (tool_id, data.id, key)
                galaxy_url = params.get("GALAXY_URL", galaxy_url)
                params = dict(URL=URL, GALAXY_URL=galaxy_url, name=data.name, info=data.info, dbkey=data.dbkey, data_type=data.ext)

                # Assume there is exactly one output file possible
                TOOL_OUTPUT_TYPE = None
                for key, obj in tool.outputs.items():
                    try:
                        TOOL_OUTPUT_TYPE = obj.format
                        params[key] = data.id
                        break
                    except Exception:
                        # exclude outputs different from ToolOutput (e.g. collections) from the previous assumption
                        continue
                if TOOL_OUTPUT_TYPE is None:
                    raise Exception("Error: ToolOutput object not found")

                original_history = trans.sa_session.query(trans.app.model.History).get(data.history_id)
                tool.execute(trans, incoming=params, history=original_history)
            else:
                log.debug('async error -> %s' % STATUS)
                trans.log_event('Async error -> %s' % STATUS)
                data.state = data.blurb = jobs.JOB_ERROR
                data.info = "Error -> %s" % STATUS

            trans.sa_session.flush()

            return "Data %s with status %s received. OK" % (data_id, STATUS)
        else:
            #
            # no data_id must be parameter submission
            #

            # need to get history, as trans.history seems to be None in async mode
            async_history = trans.sa_session.query(trans.app.model.History).filter_by(
                user=trans.get_user(),
                deleted=False).order_by(trans.app.model.History.update_time.desc()).first()
            GALAXY_TYPE = None
            if params.data_type:
                GALAXY_TYPE = params.data_type
            elif params.galaxyFileFormat == 'wig':  # this is an undocumented legacy special case
                GALAXY_TYPE = 'wig'
            elif params.GALAXY_TYPE:
                GALAXY_TYPE = params.GALAXY_TYPE
            else:
                # Assume there is exactly one output
                outputs_count = 0
                for obj in tool.outputs.values():
                    try:
                        GALAXY_TYPE = obj.format
                        outputs_count += 1
                    except Exception:
                        # exclude outputs different from ToolOutput (e.g. collections) from the previous assumption
                        # a collection object does not have the 'format' attribute, so it will throw an exception
                        continue
                if outputs_count > 1:
                    raise Exception("Error: the tool should have just one output")

            if GALAXY_TYPE is None:
                raise Exception("Error: ToolOutput object not found")

            GALAXY_NAME = params.name or params.GALAXY_NAME or '%s query' % tool.name
            GALAXY_INFO = params.info or params.GALAXY_INFO or params.galaxyDescription or ''
            GALAXY_BUILD = params.dbkey or params.GALAXY_BUILD or params.galaxyFreeze or '?'

            # data = datatypes.factory(ext=GALAXY_TYPE)()
            # data.ext   = GALAXY_TYPE
            # data.name  = GALAXY_NAME
            # data.info  = GALAXY_INFO
            # data.dbkey = GALAXY_BUILD
            # data.state = jobs.JOB_OK
            # history.datasets.add_dataset( data )
            data = trans.app.model.HistoryDatasetAssociation(create_dataset=True, sa_session=trans.sa_session, extension=GALAXY_TYPE)
            trans.app.security_agent.set_all_dataset_permissions(data.dataset, trans.app.security_agent.history_get_default_permissions(async_history))
            data.name = GALAXY_NAME
            data.dbkey = GALAXY_BUILD
            data.info = GALAXY_INFO
            trans.sa_session.add(data)  # Need to add data to session before setting state (setting state requires that the data object is in the session, but this may change)
            data.state = data.states.NEW
            async_history.add_dataset(data, genome_build=GALAXY_BUILD)
            trans.sa_session.add(async_history)
            trans.sa_session.flush()
            # we need to explicitly create the file
            data.dataset.object_store.create(data)
            trans.log_event("Added dataset %d to history %d" % (data.id, async_history.id), tool_id=tool_id)

            try:
                key = hmac_new(trans.app.config.tool_secret, "%d:%d" % (data.id, data.history_id))
                galaxy_url = trans.request.base + '/api/async/%s/%s/%s' % (tool_id, data.id, key)
                params.update({'GALAXY_URL': galaxy_url})
                params.update({'data_id': data.id})

                # Use provided URL or fallback to tool action
                url = URL or tool.action
                # Does url already have query params?
                if '?' in url:
                    url_join_char = '&'
                else:
                    url_join_char = '?'
                url = "%s%s%s" % (url, url_join_char, urlencode(params.flatten()))
                log.debug("connecting to -> %s" % url)
                trans.log_event("Async connecting to -> %s" % url)
                text = requests.get(url).text.strip()
                if not text.endswith('OK'):
                    raise Exception(text)
                data.state = data.blurb = data.states.RUNNING
            except Exception as e:
                data.info = unicodify(e)
                data.state = data.blurb = data.states.ERROR

            trans.sa_session.flush()

        return trans.fill_template('root/tool_runner.mako', out_data={}, num_jobs=1, job_errors=[])
