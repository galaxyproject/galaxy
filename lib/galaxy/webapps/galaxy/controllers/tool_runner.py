"""
Controller handles external tool related requests
"""

import logging

from markupsafe import escape

import galaxy.util
from galaxy import web
from galaxy.tools import DataSourceTool
from galaxy.web import (
    error,
    url_for,
)
from galaxy.webapps.base.controller import BaseUIController

log = logging.getLogger(__name__)


class ToolRunner(BaseUIController):
    # Hack to get biomart to work, ideally, we could pass tool_id to biomart and receive it back
    @web.expose
    def biomart(self, trans, tool_id="biomart", **kwd):
        """Catches the tool id and redirects as needed"""
        return self.index(trans, tool_id=tool_id, **kwd)

    # test to get hapmap to work, ideally, we could pass tool_id to hapmap biomart and receive it back
    @web.expose
    def hapmapmart(self, trans, tool_id="hapmapmart", **kwd):
        """Catches the tool id and redirects as needed"""
        return self.index(trans, tool_id=tool_id, **kwd)

    @web.expose
    def default(self, trans, tool_id=None, **kwd):
        """Catches the tool id and redirects as needed"""
        return self.index(trans, tool_id=tool_id, **kwd)

    def __get_tool(self, tool_id, tool_version=None, get_loaded_tools_by_lineage=False, set_selected=False):
        tool_version_select_field, tools, tool = self.get_toolbox().get_tool_components(
            tool_id, tool_version, get_loaded_tools_by_lineage, set_selected
        )
        return tool

    @web.expose
    def index(self, trans, tool_id=None, from_noframe=None, **kwd):
        def __tool_404__():
            log.debug("index called with tool id '%s' but no such tool exists", tool_id)
            trans.log_event(f"Tool id '{tool_id}' does not exist")
            trans.response.status = 404
            return trans.show_error_message(f"Tool '{escape(tool_id)}' does not exist.")

        # tool id not available, redirect to main page
        if tool_id is None:
            return trans.response.send_redirect(url_for(controller="root", action="welcome"))
        tool = self.__get_tool(tool_id)
        # tool id is not matching, display an error
        if not tool:
            return __tool_404__()
        if tool.require_login and not trans.user:
            redirect = url_for(controller="tool_runner", action="index", tool_id=tool_id, **kwd)
            return trans.response.send_redirect(
                url_for(
                    controller="user",
                    action="login",
                    cntrller="user",
                    status="info",
                    message="You must be logged in to use this tool.",
                    redirect=redirect,
                )
            )
        if not tool.allow_user_access(trans.user):
            return __tool_404__()
        # FIXME: Tool class should define behavior
        if tool.tool_type in ["default", "interactivetool"]:
            return trans.response.send_redirect(url_for(controller="root", tool_id=tool_id))

        # execute tool without displaying form
        # (used for datasource tools, but note that data_source_async tools
        # are handled separately by the async controller)
        params = galaxy.util.Params(kwd, sanitize=False).__dict__
        if tool.input_translator:
            # perform test translation of the incoming params without affecting originals
            # the actual translation will happen later
            # this is only for checking if we end up with required parameters
            test_params = params.copy()
            tool.input_translator.translate(test_params)
        else:
            test_params = params
        if tool.tool_type == "data_source":
            if "URL" not in test_params:
                error("Execution of `data_source` tools requires a `URL` parameter")
            # preserve original params sent by the remote server as extra dict
            # before in-place translation happens, then clean the incoming params
            params.update({"incoming_request_params": params.copy()})
            if tool.input_translator and tool.wants_params_cleaned:
                for k in list(params.keys()):
                    if k not in tool.input_translator.vocabulary and k not in ("URL", "incoming_request_params"):
                        # the remote server has sent a param
                        # that the tool is not expecting -> drop it
                        del params[k]
        else:
            if "runtool_btn" not in test_params:
                error("Tool execution through the `tool_runner` requires a `runtool_btn` flag")

        # We may be visiting Galaxy for the first time ( e.g., sending data from UCSC ),
        # so make sure to create a new history if we've never had one before.
        history = tool.get_default_history_by_trans(trans, create=True)
        try:
            vars = tool.handle_input(trans, params, history=history)
        except Exception as e:
            error(galaxy.util.unicodify(e))
        if len(params) > 0:
            trans.log_event(f"Tool params: {str(params)}", tool_id=tool_id)
        return trans.fill_template("root/tool_runner.mako", **vars)

    @web.expose
    def rerun(self, trans, id=None, job_id=None, **kwd):
        """
        Given a HistoryDatasetAssociation id, find the job and that created
        the dataset, extract the parameters, and display the appropriate tool
        form with parameters already filled in.
        """
        if job_id is None:
            if not id:
                error("'id' parameter is required")
            try:
                id = int(id)
            except ValueError:
                # it's not an un-encoded id, try to parse as encoded
                try:
                    id = trans.security.decode_id(id)
                except Exception:
                    error("Invalid value for 'id' parameter")
            # Get the dataset object
            data = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get(id)
            # only allow rerunning if user is allowed access to the dataset.
            if not (
                trans.user_is_admin
                or trans.app.security_agent.can_access_dataset(trans.get_current_user_roles(), data.dataset)
            ):
                error("You are not allowed to access this dataset")
            # Get the associated job, if any.
            job = data.creating_job
            if job:
                job_id = trans.security.encode_id(job.id)
            else:
                raise Exception(f"Failed to get job information for dataset hid {data.hid}")
        return trans.response.send_redirect(url_for(controller="root", job_id=job_id))

    @web.expose
    def data_source_redirect(self, trans, tool_id=None):
        """
        Redirects a user accessing a Data Source tool to its target action link.
        This method will subvert mix-mode content blocking in several browsers when
        accessing non-https data_source tools from an https galaxy server.

        Tested as working on Safari 7.0 and FireFox 26
        Subverting did not work on Chrome 31
        """
        if tool_id is None:
            return trans.response.send_redirect(url_for(controller="root", action="welcome"))
        tool = self.__get_tool(tool_id)
        # No tool matching the tool id, display an error (shouldn't happen)
        if not tool:
            log.error("data_source_redirect called with tool id '%s' but no such tool exists", tool_id)
            trans.log_event(f"Tool id '{tool_id}' does not exist")
            trans.response.status = 404
            return trans.show_error_message(f"Tool '{escape(tool_id)}' does not exist.")

        if isinstance(tool, DataSourceTool):
            link = url_for(tool.action, **tool.get_static_param_values(trans))
        else:
            link = url_for(controller="tool_runner", tool_id=tool.id)
        return trans.response.send_redirect(link)
