"""
Controller to handle communication of tools of type data_source_async
"""

import logging
from urllib.parse import urlencode

from galaxy import web
from galaxy.model.base import transaction
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    Params,
    requests,
    unicodify,
)
from galaxy.util.hash_util import hmac_new
from galaxy.webapps.base.controller import BaseUIController

log = logging.getLogger(__name__)


class ASync(BaseUIController):
    @web.expose
    def default(self, trans, tool_id=None, data_id=None, data_secret=None, **kwd):
        """Catches the tool id and redirects as needed"""
        return self.index(trans, tool_id=tool_id, data_id=data_id, data_secret=data_secret, **kwd)

    @web.expose
    def index(self, trans, tool_id=None, data_secret=None, **kwd):
        """Manages ascynchronous connections"""

        if tool_id is None:
            return "tool_id argument is required"
        tool_id = str(tool_id)

        # redirect to main when getting no parameters
        if not kwd:
            return trans.response.send_redirect("/index")

        params = Params(kwd, sanitize=False)
        data_id = params.data_id

        log.debug(f"async dataid -> {data_id}")
        trans.log_event(f"Async dataid -> {str(data_id)}")

        # initialize the tool
        toolbox = self.get_toolbox()
        tool = toolbox.get_tool(tool_id)
        if not tool:
            return f"Tool with id {tool_id} not found"

        if data_id:
            #
            # we have an incoming data_id
            #
            data = trans.sa_session.query(trans.model.HistoryDatasetAssociation).get(data_id)

            if not data:
                return f"Data {data_id} does not exist or has already been deleted"
            if data.state in data.dataset.terminal_states:
                log.debug(f"Tool {tool.id}: execution stopped as data {data_id} has entered terminal state prematurely")
                trans.log_event(
                    f"Tool {tool.id}: execution stopped as data {data_id} has entered terminal state prematurely"
                )
                return f"Data {data_id} has finished processing before job could be completed"

            # map params from the tool's <request_param_translation> section;
            # ignore any other params that may have been passed by the remote
            # server with the exception of STATUS and URL;
            # if name, info, dbkey and data_type are not handled via incoming params,
            # use the metadata from the already existing dataset;
            # preserve original params under nested dict
            params_dict = dict(
                STATUS=params.STATUS,
                URL=params.URL,
                name=data.name,
                info=data.info,
                dbkey=data.dbkey,
                data_type=data.ext,
                incoming_request_params=params.__dict__.copy(),
            )
            if tool.input_translator:
                tool.input_translator.translate(params)
                tool_declared_params = {
                    translator.galaxy_name for translator in tool.input_translator.param_trans_dict.values()
                }
                for param in params:
                    if param in tool_declared_params or not tool.wants_params_cleaned:
                        params_dict[param] = params.get(param, None)
            params = params_dict

            if not params.get("URL"):
                return f"No URL parameter was submitted for data {data_id}"

            STATUS = params.get("STATUS")

            if STATUS == "OK":
                key = hmac_new(trans.app.config.tool_secret, "%d:%d" % (data.id, data.history_id))
                if key != data_secret:
                    return f"You do not have permission to alter data {data_id}."
                if not params.get("GALAXY_URL"):
                    # provide a fallback for GALAXY_URL
                    params["GALAXY_URL"] = f"{trans.request.url_path}/async/{tool_id}/{data.id}/{key}"
                # push the job into the queue
                data.state = data.blurb = data.states.RUNNING
                log.debug(f"executing tool {tool.id}")
                trans.log_event(f"Async executing tool {tool.id}", tool_id=tool.id)

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
                job, *_ = tool.execute(trans, incoming=params, history=original_history)
                trans.app.job_manager.enqueue(job, tool=tool)
            else:
                log.debug(f"async error -> {STATUS}")
                trans.log_event(f"Async error -> {STATUS}")
                data.state = data.blurb = "error"
                data.info = f"Error -> {STATUS}"

            with transaction(trans.sa_session):
                trans.sa_session.commit()

            return f"Data {data_id} with status {STATUS} received. OK"
        else:
            # no data_id must be parameter submission
            #
            # create new dataset, put it into running state,
            # send request for data to remote server and see if the response
            # ends in ok;
            # the request that's getting sent goes to the URL found in
            # params.URL or, in its absence, to the one found as the value of
            # the "action" attribute of the data source tool's "inputs" tag.
            # Included in the request are the parameters:
            # - data_id, which indicates to the remote server that Galaxy is
            #   ready to accept data
            # - GALAXY_URL, which takes the form:
            #   {base_url}/async/{tool_id}/{data_id}/{data_secret}, and which
            #   when used by the remote server to send a data download link,
            #   will trigger the if branch above.
            GALAXY_TYPE = None
            if params.data_type:
                GALAXY_TYPE = params.data_type
            elif params.galaxyFileFormat == "wig":  # this is an undocumented legacy special case
                GALAXY_TYPE = "wig"
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

            GALAXY_NAME = params.name or params.GALAXY_NAME or f"{tool.name} query"
            GALAXY_INFO = params.info or params.GALAXY_INFO or params.galaxyDescription or ""
            GALAXY_BUILD = params.dbkey or params.GALAXY_BUILD or params.galaxyFreeze or "?"

            # data = datatypes.factory(ext=GALAXY_TYPE)()
            # data.ext   = GALAXY_TYPE
            # data.name  = GALAXY_NAME
            # data.info  = GALAXY_INFO
            # data.dbkey = GALAXY_BUILD
            # data.state = jobs.JOB_OK
            # history.datasets.add_dataset( data )

            data = trans.app.model.HistoryDatasetAssociation(
                create_dataset=True, sa_session=trans.sa_session, extension=GALAXY_TYPE
            )
            trans.app.security_agent.set_all_dataset_permissions(
                data.dataset, trans.app.security_agent.history_get_default_permissions(trans.history)
            )
            data.name = GALAXY_NAME
            data.dbkey = GALAXY_BUILD
            data.info = GALAXY_INFO
            trans.sa_session.add(
                data
            )  # Need to add data to session before setting state (setting state requires that the data object is in the session, but this may change)
            data.state = data.states.NEW
            trans.history.add_dataset(data, genome_build=GALAXY_BUILD)
            trans.sa_session.add(trans.history)
            with transaction(trans.sa_session):
                trans.sa_session.commit()
            # Need to explicitly create the file
            data.dataset.object_store.create(data.dataset)
            trans.log_event("Added dataset %d to history %d" % (data.id, trans.history.id), tool_id=tool_id)

            try:
                key = hmac_new(trans.app.config.tool_secret, "%d:%d" % (data.id, data.history_id))
                galaxy_url = f"{trans.request.url_path}/async/{tool_id}/{data.id}/{key}"
                params.update({"GALAXY_URL": galaxy_url})
                params.update({"data_id": data.id})

                # Use provided URL or fallback to tool action
                url = params.URL or tool.action
                # Does url already have query params?
                if "?" in url:
                    url_join_char = "&"
                else:
                    url_join_char = "?"
                url = f"{url}{url_join_char}{urlencode(params.flatten())}"
                log.debug(f"connecting to -> {url}")
                trans.log_event(f"Async connecting to -> {url}")
                text = requests.get(url, timeout=DEFAULT_SOCKET_TIMEOUT).text.strip()
                if not text.endswith("OK"):
                    raise Exception(text)
                data.state = data.blurb = data.states.RUNNING
            except Exception as e:
                data.info = unicodify(e)
                data.state = data.blurb = data.states.ERROR

            with transaction(trans.sa_session):
                trans.sa_session.commit()

        return trans.fill_template("root/tool_runner.mako", out_data={}, num_jobs=1, job_errors=[])
