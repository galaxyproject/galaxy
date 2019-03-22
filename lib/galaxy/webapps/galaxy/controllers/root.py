"""
Contains the main interface in the Universe class
"""
from __future__ import absolute_import

import logging
import os

import requests
from webob.compat import cgi_FieldStorage
from webob.exc import (
    HTTPBadGateway,
    HTTPNotFound
)

from galaxy import (
    managers,
    web
)
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.util import (
    FILENAME_VALID_CHARS,
    listify,
    string_as_bool
)
from galaxy.web.base import controller

log = logging.getLogger(__name__)


# =============================================================================
class RootController(controller.JSAppLauncher, UsesAnnotations):
    """
    Controller class that maps to the url root of Galaxy (i.e. '/').
    """

    def __init__(self, app):
        super(RootController, self).__init__(app)
        self.history_manager = managers.histories.HistoryManager(app)
        self.history_serializer = managers.histories.HistorySerializer(app)

    @web.expose
    def default(self, trans, target1=None, target2=None, **kwd):
        """
        Called on any url that does not match a controller method.
        """
        raise HTTPNotFound('This link may not be followed from within Galaxy.')

    @web.expose
    def index(self, trans, tool_id=None, workflow_id=None, history_id=None, m_c=None, m_a=None, **kwd):
        """
        Root and entry point for client-side web app.

        :type       tool_id: str or None
        :param      tool_id: load center panel with given tool if not None
        :type   workflow_id: encoded id or None
        :param  workflow_id: load center panel with given workflow if not None
        :type    history_id: encoded id or None
        :param   history_id: switch current history to given history if not None
        :type           m_c: str or None
        :param          m_c: controller name (e.g. 'user')
        :type           m_a: str or None
        :param          m_a: controller method/action (e.g. 'dbkeys')

        If m_c and m_a are present, the center panel will be loaded using the
        controller and action as a url: (e.g. 'user/dbkeys').
        """

        self._check_require_login(trans)

        # if a history_id was sent, attempt to switch to that history
        history = trans.history
        if history_id:
            unencoded_id = trans.security.decode_id(history_id)
            history = self.history_manager.get_owned(unencoded_id, trans.user)
            trans.set_history(history)

        return self._bootstrapped_client(trans)

    @web.expose
    def login(self, trans, redirect=None, **kwd):
        """
        User login path for client-side.
        """
        return self.template(trans, 'login',
                             redirect=redirect,
                             # an installation may have it's own welcome_url - show it here if they've set that
                             welcome_url=web.url_for(controller='root', action='welcome'),
                             show_welcome_with_login=trans.app.config.show_welcome_with_login)

    # ---- Tool related -----------------------------------------------------

    @web.json
    def tool_search(self, trans, **kwd):
        """Searches the tool database and returns data for any tool
        whose text matches the query.

        Data are returned in JSON format.
        """
        query = kwd.get('query', '')
        tags = listify(kwd.get('tags[]', []))
        trans.log_action(trans.get_user(), "tool_search.search", "", {"query": query, "tags": tags})
        results = []
        if tags:
            tags = trans.sa_session.query(trans.app.model.Tag).filter(trans.app.model.Tag.name.in_(tags)).all()
            for tagged_tool_il in [tag.tagged_tools for tag in tags]:
                for tagged_tool in tagged_tool_il:
                    if tagged_tool.tool_id not in results:
                        results.append(tagged_tool.tool_id)
            if trans.user:
                trans.user.preferences['selected_tool_tags'] = ','.join([tag.name for tag in tags])
                trans.sa_session.flush()
        elif trans.user:
            trans.user.preferences['selected_tool_tags'] = ''
            trans.sa_session.flush()
        if len(query) > 2:
            search_results = trans.app.toolbox_search.search(query)
            if 'tags[]' in kwd:
                results = [x for x in search_results if x in results]
            else:
                results = search_results
        return results

    @web.expose
    def tool_help(self, trans, id):
        """Return help page for tool identified by 'id' if available
        """
        toolbox = self.get_toolbox()
        tool = toolbox.get_tool(id)
        yield "<html><body>"
        if not tool:
            # TODO: arent tool ids strings now?
            yield "Unknown tool id '%d'" % id
        elif tool.help:
            yield tool.help
        else:
            yield "No additional help available for tool '%s'" % tool.name
        yield "</body></html>"

    # ---- Dataset display / editing ----------------------------------------
    @web.expose
    def display(self, trans, id=None, hid=None, tofile=None, toext=".txt", encoded_id=None, **kwd):
        """Returns data directly into the browser.

        Sets the mime-type according to the extension.

        Used by the twill tool test driver - used anywhere else? Would like to drop hid
        argument and path if unneeded now. Likewise, would like to drop encoded_id=XXX
        and use assume id is encoded (likely id wouldn't be coming in encoded if this
        is used anywhere else though.)
        """
        # TODO: unencoded id
        if hid is not None:
            try:
                hid = int(hid)
            except ValueError:
                return "hid '%s' is invalid" % str(hid)
            history = trans.get_history()
            for dataset in history.datasets:
                if dataset.hid == hid:
                    data = dataset
                    break
            else:
                raise Exception("No dataset with hid '%d'" % hid)
        else:
            if encoded_id and not id:
                id = self.decode_id(encoded_id)
            try:
                data = trans.sa_session.query(self.app.model.HistoryDatasetAssociation).get(id)
            except Exception:
                return "Dataset id '%s' is invalid" % str(id)
        if data:
            current_user_roles = trans.get_current_user_roles()
            if trans.app.security_agent.can_access_dataset(current_user_roles, data.dataset):
                trans.response.set_content_type(data.get_mime())
                if tofile:
                    fStat = os.stat(data.file_name)
                    trans.response.headers['Content-Length'] = int(fStat.st_size)
                    if toext[0:1] != ".":
                        toext = "." + toext
                    fname = data.name
                    fname = ''.join(c in FILENAME_VALID_CHARS and c or '_' for c in fname)[0:150]
                    trans.response.headers["Content-Disposition"] = 'attachment; filename="GalaxyHistoryItem-%s-[%s]%s"' % (data.hid, fname, toext)
                trans.log_event("Display dataset id: %s" % str(id))
                try:
                    return open(data.file_name, 'rb')
                except Exception:
                    return "This dataset contains no content"
            else:
                return "You are not allowed to access this dataset"
        else:
            return "No dataset with id '%s'" % str(id)

    @web.expose
    def display_as(self, trans, id=None, display_app=None, **kwd):
        """Returns a file in a format that can successfully be displayed in display_app.
        """
        # TODO: unencoded id
        data = trans.sa_session.query(self.app.model.HistoryDatasetAssociation).get(id)
        authz_method = 'rbac'
        if 'authz_method' in kwd:
            authz_method = kwd['authz_method']
        if data:
            current_user_roles = trans.get_current_user_roles()
            if authz_method == 'rbac' and trans.app.security_agent.can_access_dataset(current_user_roles, data):
                trans.response.set_content_type(data.get_mime())
                trans.log_event("Formatted dataset id %s for display at %s" % (str(id), display_app))
                return data.as_display_type(display_app, **kwd)
            elif authz_method == 'display_at' and trans.app.host_security_agent.allow_action(trans.request.remote_addr,
                                                                                             data.permitted_actions.DATASET_ACCESS,
                                                                                             dataset=data):
                trans.response.set_content_type(data.get_mime())
                return data.as_display_type(display_app, **kwd)
            else:
                return "You are not allowed to access this dataset."
        else:
            return "No data with id=%d" % id

    # ---- History management -----------------------------------------------
    @web.expose
    def history_delete(self, trans, id):
        """Backward compatibility with check_galaxy script.
        """
        # TODO: unused?
        return trans.webapp.controllers['history'].list(trans, id, operation='delete')

    @web.expose
    def clear_history(self, trans):
        """Clears the history for a user.
        """
        # TODO: unused? (seems to only be used in TwillTestCase)
        history = trans.get_history()
        for dataset in history.datasets:
            dataset.deleted = True
            dataset.clear_associated_files()
        trans.sa_session.flush()
        trans.log_event("History id %s cleared" % (str(history.id)))
        trans.response.send_redirect(web.url_for("/index"))

    @web.expose
    def history_import(self, trans, id=None, confirm=False, **kwd):
        # TODO: unused?
        # TODO: unencoded id
        user = trans.get_user()
        user_history = trans.get_history()
        if not id:
            return trans.show_error_message("You must specify a history you want to import.")
        import_history = trans.sa_session.query(trans.app.model.History).get(id)
        if not import_history:
            return trans.show_error_message("The specified history does not exist.")
        if user:
            if import_history.user_id == user.id:
                return trans.show_error_message("You cannot import your own history.")
            new_history = import_history.copy(target_user=trans.user)
            new_history.name = "imported: " + new_history.name
            new_history.user_id = user.id
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.sa_session.query(trans.app.model.GalaxySessionToHistoryAssociation) \
                                              .filter_by(session_id=galaxy_session.id, history_id=new_history.id) \
                                              .first()
            except Exception:
                association = None
            new_history.add_galaxy_session(galaxy_session, association=association)
            trans.sa_session.add(new_history)
            trans.sa_session.flush()
            if not user_history.datasets:
                trans.set_history(new_history)
            trans.log_event("History imported, id: %s, name: '%s': " % (str(new_history.id), new_history.name))
            return trans.show_ok_message("""
                History "%s" has been imported. Click <a href="%s">here</a>
                to begin.""" % (new_history.name, web.url_for('/')))
        elif not user_history.datasets or confirm:
            new_history = import_history.copy()
            new_history.name = "imported: " + new_history.name
            new_history.user_id = None
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.sa_session.query(trans.app.model.GalaxySessionToHistoryAssociation) \
                                              .filter_by(session_id=galaxy_session.id, history_id=new_history.id) \
                                              .first()
            except Exception:
                association = None
            new_history.add_galaxy_session(galaxy_session, association=association)
            trans.sa_session.add(new_history)
            trans.sa_session.flush()
            trans.set_history(new_history)
            trans.log_event("History imported, id: %s, name: '%s': " % (str(new_history.id), new_history.name))
            return trans.show_ok_message("""
                History "%s" has been imported. Click <a href="%s">here</a>
                to begin.""" % (new_history.name, web.url_for('/')))
        return trans.show_warn_message("""
            Warning! If you import this history, you will lose your current
            history. Click <a href="%s">here</a> to confirm.
            """ % web.url_for(controller='root', action='history_import', id=id, confirm=True))

    @web.expose
    def history_new(self, trans, name=None):
        """Create a new history with the given name
        and refresh the history panel.
        """
        trans.new_history(name=name)
        trans.log_event("Created new History, id: %s." % str(trans.history.id))
        return trans.show_message("New history created", refresh_frames=['history'])

    @web.expose
    def history_add_to(self, trans, history_id=None, file_data=None,
                       name="Data Added to History", info=None, ext="txt", dbkey="?", copy_access_from=None, **kwd):
        """Adds a POSTed file to a History.
        """
        # TODO: unencoded id
        try:
            history = trans.sa_session.query(trans.app.model.History).get(history_id)
            data = trans.app.model.HistoryDatasetAssociation(name=name,
                                                             info=info,
                                                             extension=ext,
                                                             dbkey=dbkey,
                                                             create_dataset=True,
                                                             sa_session=trans.sa_session)
            if copy_access_from:
                copy_access_from = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get(copy_access_from)
                trans.app.security_agent.copy_dataset_permissions(copy_access_from.dataset, data.dataset)
            else:
                permissions = trans.app.security_agent.history_get_default_permissions(history)
                trans.app.security_agent.set_all_dataset_permissions(data.dataset, permissions)
            trans.sa_session.add(data)
            trans.sa_session.flush()
            data_file = open(data.file_name, "wb")
            file_data.file.seek(0)
            data_file.write(file_data.file.read())
            data_file.close()
            data.state = data.states.OK
            data.set_size()
            data.init_meta()
            data.set_meta()
            trans.sa_session.flush()
            history.add_dataset(data)
            trans.sa_session.flush()
            data.set_peek()
            trans.sa_session.flush()
            trans.log_event("Added dataset %d to history %d" % (data.id, trans.history.id))
            return trans.show_ok_message("Dataset " + str(data.hid) + " added to history " + str(history_id) + ".")
        except Exception as e:
            msg = "Failed to add dataset to history: %s" % (e)
            log.error(msg)
            trans.log_event(msg)
            return trans.show_error_message("Adding File to History has Failed")

    @web.expose
    def dataset_make_primary(self, trans, id=None):
        """Copies a dataset and makes primary.
        """
        # TODO: unused?
        # TODO: unencoded id
        try:
            old_data = trans.sa_session.query(self.app.model.HistoryDatasetAssociation).get(id)
            new_data = old_data.copy()
            # new_data.parent = None
            history = trans.get_history()
            history.add_dataset(new_data)
            trans.sa_session.add(new_data)
            trans.sa_session.flush()
            return trans.show_message("<p>Secondary dataset has been made primary.</p>", refresh_frames=['history'])
        except Exception:
            return trans.show_error_message("<p>Failed to make secondary dataset primary.</p>")

    @web.expose
    def welcome(self, trans):
        welcome_url = trans.app.config.welcome_url
        return trans.response.send_redirect(web.url_for(welcome_url))

    @web.expose
    def bucket_proxy(self, trans, bucket=None, **kwd):
        if bucket:
            trans.response.set_content_type('text/xml')
            b_list_xml = requests.get('http://s3.amazonaws.com/%s/' % bucket)
            return b_list_xml.text
        raise Exception("You must specify a bucket")

    # ---- Debug methods ----------------------------------------------------
    @web.expose
    def echo(self, trans, **kwd):
        """Echos parameters (debugging).
        """
        rval = ""
        for k in trans.request.headers:
            rval += "%s: %s <br/>" % (k, trans.request.headers[k])
        for k in kwd:
            rval += "%s: %s <br/>" % (k, kwd[k])
            if isinstance(kwd[k], cgi_FieldStorage):
                rval += "-> %s" % kwd[k].file.read()
        return rval

    @web.json
    def echo_json(self, trans, **kwd):
        """Echos parameters as JSON (debugging).

        Attempts to parse values passed as boolean, float, then int. Defaults
        to string. Non-recursive (will not parse lists).
        """
        # TODO: use json
        rval = {}
        for k in kwd:
            rval[k] = kwd[k]
            try:
                if rval[k] in ['true', 'True', 'false', 'False']:
                    rval[k] = string_as_bool(rval[k])
                rval[k] = float(rval[k])
                rval[k] = int(rval[k])
            except Exception:
                pass
        return rval

    @web.expose
    def generate_error(self, trans, code=500):
        """Raises an exception (debugging).
        """
        trans.response.status = code
        raise Exception("Fake error!")

    @web.json
    def generate_json_error(self, trans, code=500):
        """Raises an exception (debugging).
        """
        try:
            code = int(code)
        except ValueError:
            code = 500

        if code == 502:
            raise HTTPBadGateway()
        trans.response.status = code
        return {'error': 'Fake error!'}
