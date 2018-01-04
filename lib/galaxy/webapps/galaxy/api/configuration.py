"""
API operations allowing clients to determine Galaxy instance's capabilities
and configuration settings.
"""
import inspect
import json
import logging
import os
import re
from collections import OrderedDict

from galaxy.managers import configuration, users
from galaxy.queue_worker import send_control_task
from galaxy.web import (
    _future_expose_api as expose_api,
    _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless,
    expose,
    require_admin
)
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class ConfigurationController(BaseAPIController):

    def __init__(self, app):
        super(ConfigurationController, self).__init__(app)
        self.config_serializer = configuration.ConfigSerializer(app)
        self.admin_config_serializer = configuration.AdminConfigSerializer(app)
        self.user_manager = users.UserManager(app)

    @expose
    def api_docs(self, trans, **kwd):
        """
        GET /api/docs

        :returns: Returns basic API documentation as HTML
        :rtype:   string

        """
        def format_methods(r):
            if r.conditions:
                method = r.conditions.get('method', '')
                return type(method) is str and method or ', '.join(method)
            else:
                return ''

        route_paths = {}
        # see also mapper.__str__()
        for r in trans.webapp.mapper.matchlist:
            if r.routepath.startswith('api/'):
                controller_name = r.defaults.get('controller', '')
                controller = trans.webapp.api_controllers.get(controller_name, None)

                action = r.defaults.get('action', '')
                if r.routepath:
                    a_doc = inspect.getdoc(getattr(controller, action, controller))
                    route_dict = OrderedDict([
                        ('Action', action),
                        ('Description', a_doc),
                        ('Route_name', r.name or ''),
                        ('Methods', format_methods(r)),
                        ('Controller', controller_name),
                    ])
                    if r.routepath in route_paths:
                        route_paths[r.routepath].append(route_dict)
                    else:
                        route_paths[r.routepath] = [route_dict]

        # This should probably go in a .mako
        body = '<html><body><ul>{url_list}</ul></body></html>'
        url_list = ''
        for routepath in sorted(route_paths.keys()):
            url_template = '<a href="{routepath_url}">{routepath}</a>'
            if re.search(r'[:({]', routepath):
                url_template = '<a href="{routepath_url}" style="pointer-events: none;">{routepath}</a>'
            url_template = url_template.format(routepath_url=routepath.replace('api/', ''), routepath=routepath)
            for route_dict in route_paths[routepath]:
                url_template += '<details><summary><strong>{Methods}</strong> &raquo; {Action}</summary>'\
                                '<div><pre>{Description}\n'\
                                'Route name: {Route_name}\n'\
                                'Methods: {Methods}\n'\
                                'Controller: {Controller}'\
                                '</pre></div>'\
                                '</details><br />'.format(routepath=routepath, **route_dict)
            url_list += '<li>' + url_template + '</li>'
        body = body.format(url_list=url_list)
        return body

    @expose_api
    def whoami(self, trans, **kwd):
        """
        GET /api/whoami
        Return information about the current authenticated user.

        :returns: dictionary with user information
        :rtype:   dict
        """
        current_user = self.user_manager.current_user(trans)
        return current_user.to_dict()

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwd):
        """
        GET /api/configuration
        Return an object containing exposable configuration settings.

        Note: a more complete list is returned if the user is an admin.
        """
        is_admin = trans.user_is_admin()
        serialization_params = self._parse_serialization_params(kwd, 'all')
        return self.get_config_dict(trans, is_admin, **serialization_params)

    @expose_api_anonymous_and_sessionless
    def version(self, trans, **kwds):
        """
        GET /api/version
        Return a description of the major version of Galaxy (e.g. 15.03).

        :rtype:     dict
        :returns:   dictionary with major version keyed on 'version_major'
        """
        extra = {}
        try:
            version_file = os.environ.get("GALAXY_VERSION_JSON_FILE", self.app.container_finder.app_info.galaxy_root_dir + "/version.json")
            with open(version_file, "r") as f:
                extra = json.load(f)
        except Exception:
            pass
        return {"version_major": self.app.config.version_major, "extra": extra}

    def get_config_dict(self, trans, return_admin=False, view=None, keys=None, default_view='all'):
        """
        Return a dictionary with (a subset of) current Galaxy settings.

        If `return_admin` also include a subset of more sensitive keys.
        Pass in `view` (String) and comma seperated list of keys to control which
        configuration settings are returned.
        """
        serializer = self.config_serializer
        if return_admin:
            # TODO: this should probably just be under a different route: 'admin/configuration'
            serializer = self.admin_config_serializer

        serialized = serializer.serialize_to_view(self.app.config, view=view, keys=keys, default_view=default_view)
        return serialized

    @expose_api
    @require_admin
    def dynamic_tool_confs(self, trans):
        confs = self.app.toolbox.dynamic_confs(include_migrated_tool_conf=True)
        return list(map(_tool_conf_to_dict, confs))

    @expose_api
    @require_admin
    def decode_id(self, trans, encoded_id, **kwds):
        """Decode a given id."""
        decoded_id = None
        # Handle the special case for library folders
        if ((len(encoded_id) % 16 == 1) and encoded_id.startswith('F')):
            decoded_id = trans.security.decode_id(encoded_id[1:])
        else:
            decoded_id = trans.security.decode_id(encoded_id)
        return {"decoded_id": decoded_id}

    @expose_api
    @require_admin
    def tool_lineages(self, trans):
        rval = []
        for id, tool in self.app.toolbox.tools():
            if hasattr(tool, 'lineage'):
                lineage_dict = tool.lineage.to_dict()
            else:
                lineage_dict = None

            entry = dict(
                id=id,
                lineage=lineage_dict
            )
            rval.append(entry)
        return rval

    @expose_api
    @require_admin
    def reload_toolbox(self, trans, **kwds):
        """
        PUT /api/configuration/toolbox
        Reload the Galaxy toolbox (but not individual tools).
        """
        send_control_task(self.app.toolbox.app, 'reload_toolbox')


def _tool_conf_to_dict(conf):
    return dict(
        config_filename=conf['config_filename'],
        tool_path=conf['tool_path'],
    )
