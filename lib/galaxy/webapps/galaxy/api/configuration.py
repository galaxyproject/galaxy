"""
API operations allowing clients to determine Galaxy instance's capabilities
and configuration settings.
"""

from galaxy.web import _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import require_admin
from galaxy.web.base.controller import BaseAPIController
from galaxy.managers import configuration

import logging
log = logging.getLogger( __name__ )


class ConfigurationController( BaseAPIController ):

    def __init__( self, app ):
        super( ConfigurationController, self ).__init__( app )
        self.config_serializer = configuration.ConfigSerializer( app )
        self.admin_config_serializer = configuration.AdminConfigSerializer( app )

    @expose_api_anonymous_and_sessionless
    def index( self, trans, **kwd ):
        """
        GET /api/configuration
        Return an object containing exposable configuration settings.

        Note: a more complete list is returned if the user is an admin.
        """
        is_admin = self.user_manager.is_admin( trans.user )
        serialization_params = self._parse_serialization_params( kwd, 'all' )
        return self.get_config_dict( trans, is_admin, **serialization_params )

    @expose_api_anonymous_and_sessionless
    def version( self, trans, **kwds ):
        """
        GET /api/version
        Return a description of the major version of Galaxy (e.g. 15.03).

        :rtype:     dict
        :returns:   dictionary with major version keyed on 'version_major'
        """
        return {"version_major": self.app.config.version_major }

    def get_config_dict( self, trans, return_admin=False, view=None, keys=None, default_view='all' ):
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

        serialized = serializer.serialize_to_view( self.app.config, view=view, keys=keys, default_view=default_view )
        return serialized

    @expose_api
    @require_admin
    def dynamic_tool_confs(self, trans):
        confs = self.app.toolbox.dynamic_confs(include_migrated_tool_conf=True)
        return map(_tool_conf_to_dict, confs)

    @expose_api
    @require_admin
    def tool_lineages(self, trans):
        rval = []
        for id, tool in self.app.toolbox.tools():
            if hasattr( tool, 'lineage' ):
                lineage_dict = tool.lineage.to_dict()
            else:
                lineage_dict = None

            entry = dict(
                id=id,
                lineage=lineage_dict
            )
            rval.append(entry)
        return rval


def _tool_conf_to_dict(conf):
    return dict(
        config_filename=conf['config_filename'],
        tool_path=conf['tool_path'],
    )
