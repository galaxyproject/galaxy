"""
Provides factory methods to assemble the Galaxy web application
"""

import os
import sys
import threading
import atexit

try:
    import configparser
except:
    import ConfigParser as configparser


import galaxy.app
import galaxy.model
import galaxy.model.mapping
import galaxy.datatypes.registry
import galaxy.web.framework
import galaxy.web.framework.webapp
from galaxy.webapps.util import build_template_error_formatters
from galaxy import util
from galaxy.util import asbool
from galaxy.util.postfork import process_is_uwsgi, register_postfork_function
from galaxy.util.properties import load_app_properties

from paste import httpexceptions

import logging
log = logging.getLogger( __name__ )


class GalaxyWebApplication( galaxy.web.framework.webapp.WebApplication ):
    pass


def app_factory( global_conf, **kwargs ):
    return paste_app_factory( global_conf, **kwargs )


def paste_app_factory( global_conf, **kwargs ):
    """
    Return a wsgi application serving the root object
    """
    kwargs = load_app_properties(
        kwds=kwargs
    )
    # Create the Galaxy application unless passed in
    if 'app' in kwargs:
        app = kwargs.pop( 'app' )
        galaxy.app.app = app
    else:
        try:
            app = galaxy.app.UniverseApplication( global_conf=global_conf, **kwargs )
            galaxy.app.app = app
        except:
            import traceback
            traceback.print_exc()
            sys.exit( 1 )
    # Call app's shutdown method when the interpeter exits, this cleanly stops
    # the various Galaxy application daemon threads
    atexit.register( app.shutdown )
    # Create the universe WSGI application
    webapp = GalaxyWebApplication( app, session_cookie='galaxysession', name='galaxy' )

    # CLIENTSIDE ROUTES
    # The following are routes that are handled completely on the clientside.
    # The following routes don't bootstrap any information, simply provide the
    # base analysis interface at which point the application takes over.

    webapp.add_client_route( '/tours' )
    webapp.add_client_route( '/tours/{tour_id}' )
    webapp.add_client_route( '/users' )

    # STANDARD CONTROLLER ROUTES
    webapp.add_ui_controllers( 'galaxy.webapps.galaxy.controllers', app )
    # Force /history to go to view of current
    webapp.add_route( '/history', controller='history', action='view' )
    webapp.add_route( '/history/view/{id}', controller='history', action='view' )
    # Force /activate to go to the controller
    webapp.add_route( '/activate', controller='user', action='activate' )
    webapp.add_route( '/login', controller='root', action='login' )

    # These two routes handle our simple needs at the moment
    webapp.add_route( '/async/{tool_id}/{data_id}/{data_secret}', controller='async', action='index', tool_id=None, data_id=None, data_secret=None )
    webapp.add_route( '/{controller}/{action}', action='index' )
    webapp.add_route( '/{action}', controller='root', action='index' )

    # allow for subdirectories in extra_files_path
    webapp.add_route( '/datasets/{dataset_id}/display/{filename:.+?}', controller='dataset', action='display', dataset_id=None, filename=None)
    webapp.add_route( '/datasets/{dataset_id}/{action}/{filename}', controller='dataset', action='index', dataset_id=None, filename=None)
    webapp.add_route( '/display_application/{dataset_id}/{app_name}/{link_name}/{user_id}/{app_action}/{action_param}/{action_param_extra:.+?}',
                      controller='dataset', action='display_application', dataset_id=None, user_id=None,
                      app_name=None, link_name=None, app_action=None, action_param=None, action_param_extra=None )
    webapp.add_route( '/u/{username}/d/{slug}/{filename}', controller='dataset', action='display_by_username_and_slug', filename=None )
    webapp.add_route( '/u/{username}/p/{slug}', controller='page', action='display_by_username_and_slug' )
    webapp.add_route( '/u/{username}/h/{slug}', controller='history', action='display_by_username_and_slug' )
    webapp.add_route( '/u/{username}/w/{slug}', controller='workflow', action='display_by_username_and_slug' )
    webapp.add_route( '/u/{username}/w/{slug}/{format}', controller='workflow', action='display_by_username_and_slug' )
    webapp.add_route( '/u/{username}/v/{slug}', controller='visualization', action='display_by_username_and_slug' )
    webapp.add_route( '/search', controller='search', action='index' )

    # TODO: Refactor above routes into external method to allow testing in
    # isolation as well.
    populate_api_routes( webapp, app )

    # ==== Done
    # Indicate that all configuration settings have been provided
    webapp.finalize_config()

    # Wrap the webapp in some useful middleware
    if kwargs.get( 'middleware', True ):
        webapp = wrap_in_middleware( webapp, global_conf, **kwargs )
    if asbool( kwargs.get( 'static_enabled', True) ):
        if process_is_uwsgi:
            log.error("Static middleware is enabled in your configuration but this is a uwsgi process.  Refusing to wrap in static middleware.")
        else:
            webapp = wrap_in_static( webapp, global_conf, plugin_frameworks=[ app.visualizations_registry ], **kwargs )
    # Close any pooled database connections before forking
    try:
        galaxy.model.mapping.metadata.bind.dispose()
    except:
        log.exception("Unable to dispose of pooled galaxy model database connections.")
    try:
        # This model may not actually be bound.
        if galaxy.model.tool_shed_install.mapping.metadata.bind:
            galaxy.model.tool_shed_install.mapping.metadata.bind.dispose()
    except:
        log.exception("Unable to dispose of pooled toolshed install model database connections.")

    register_postfork_function(postfork_setup)

    for th in threading.enumerate():
        if th.is_alive():
            log.debug("Prior to webapp return, Galaxy thread %s is alive.", th)
    # Return
    return webapp


def uwsgi_app_factory():
    import uwsgi
    root = os.path.abspath(uwsgi.opt.get('galaxy_root', os.getcwd()))
    config_file = uwsgi.opt.get('galaxy_config_file', os.path.join(root, 'config', 'galaxy.ini'))
    global_conf = {
        '__file__': config_file if os.path.exists(__file__) else None,
        'here': root }
    parser = configparser.ConfigParser()
    parser.read(config_file)
    try:
        kwargs = dict(parser.items('app:main'))
    except configparser.NoSectionError:
        kwargs = {}
    return app_factory(global_conf, **kwargs)


def postfork_setup():
    from galaxy.app import app
    if process_is_uwsgi:
        import uwsgi
        app.config.server_name += ".%s" % uwsgi.worker_id()
    app.control_worker.bind_and_start()


def populate_api_routes( webapp, app ):
    webapp.add_api_controllers( 'galaxy.webapps.galaxy.api', app )

    valid_history_contents_types = [
        'dataset',
        'dataset_collection',
    ]

    # Accesss HDA details via histories/{history_id}/contents/datasets/{hda_id}
    webapp.mapper.resource( "content_typed",
                            "{type:%s}s" % "|".join( valid_history_contents_types ),
                            name_prefix="history_",
                            controller='history_contents',
                            path_prefix='/api/histories/{history_id}/contents',
                            parent_resources=dict( member_name='history', collection_name='histories' ),
                            )

    contents_archive_mapper = webapp.mapper.submapper( action='archive', controller='history_contents' )
    contents_archive_mapper.connect( '/api/histories/{history_id}/contents/archive' )
    contents_archive_mapper.connect( '/api/histories/{history_id}/contents/archive/{filename}{.format}' )

    # Legacy access to HDA details via histories/{history_id}/contents/{hda_id}
    webapp.mapper.resource( 'content',
                            'contents',
                            controller='history_contents',
                            name_prefix='history_',
                            path_prefix='/api/histories/{history_id}',
                            parent_resources=dict( member_name='history', collection_name='histories' ) )
    webapp.mapper.connect( "history_contents_display",
                           "/api/histories/{history_id}/contents/{history_content_id}/display",
                           controller="datasets",
                           action="display",
                           conditions=dict(method=["GET"]))
    webapp.mapper.connect( "history_contents_metadata_file",
                           "/api/histories/{history_id}/contents/{history_content_id}/metadata_file",
                           controller="datasets",
                           action="get_metadata_file",
                           conditions=dict(method=["GET"]))
    webapp.mapper.resource( 'user',
                            'users',
                            controller='group_users',
                            name_prefix='group_',
                            path_prefix='/api/groups/{group_id}',
                            parent_resources=dict( member_name='group', collection_name='groups' ) )
    webapp.mapper.resource( 'role',
                            'roles',
                            controller='group_roles',
                            name_prefix='group_',
                            path_prefix='/api/groups/{group_id}',
                            parent_resources=dict( member_name='group', collection_name='groups' ) )
    _add_item_tags_controller( webapp,
                               name_prefix="history_content_",
                               path_prefix='/api/histories/{history_id}/contents/{history_content_id}' )
    webapp.mapper.connect( '/api/histories/published', action='published', controller="histories", conditions=dict( method=[ "GET" ] ) )
    webapp.mapper.connect( '/api/histories/shared_with_me', action='shared_with_me', controller="histories" )
    _add_item_tags_controller( webapp,
                               name_prefix="history_",
                               path_prefix='/api/histories/{history_id}' )
    _add_item_tags_controller( webapp,
                               name_prefix="workflow_",
                               path_prefix='/api/workflows/{workflow_id}' )
    _add_item_annotation_controller( webapp,
                                     name_prefix="history_content_",
                                     path_prefix='/api/histories/{history_id}/contents/{history_content_id}' )
    _add_item_annotation_controller( webapp,
                                     name_prefix="history_",
                                     path_prefix='/api/histories/{history_id}' )
    _add_item_annotation_controller( webapp,
                                     name_prefix="workflow_",
                                     path_prefix='/api/workflows/{workflow_id}' )
    _add_item_provenance_controller( webapp,
                                     name_prefix="history_content_",
                                     path_prefix='/api/histories/{history_id}/contents/{history_content_id}' )

    webapp.mapper.resource( 'dataset', 'datasets', path_prefix='/api' )
    webapp.mapper.resource( 'tool_data', 'tool_data', path_prefix='/api' )
    webapp.mapper.connect( '/api/tool_data/{id:.+?}/fields/{value:.+?}/files/{path:.+?}', action='download_field_file', controller="tool_data" )
    webapp.mapper.connect( '/api/tool_data/{id:.+?}/fields/{value:.+?}', action='show_field', controller="tool_data" )
    webapp.mapper.connect( '/api/tool_data/{id:.+?}/reload', action='reload', controller="tool_data" )
    webapp.mapper.resource( 'dataset_collection', 'dataset_collections', path_prefix='/api/')
    webapp.mapper.resource( 'sample', 'samples', path_prefix='/api' )
    webapp.mapper.resource( 'request', 'requests', path_prefix='/api' )
    webapp.mapper.resource( 'form', 'forms', path_prefix='/api' )
    webapp.mapper.resource( 'request_type', 'request_types', path_prefix='/api' )
    webapp.mapper.resource( 'role', 'roles', path_prefix='/api' )
    webapp.mapper.connect( '/api/ftp_files', controller='remote_files' )
    webapp.mapper.resource( 'remote_file', 'remote_files', path_prefix='/api' )
    webapp.mapper.resource( 'group', 'groups', path_prefix='/api' )
    webapp.mapper.resource_with_deleted( 'quota', 'quotas', path_prefix='/api' )

    # =======================
    # ====== TOOLS API ======
    # =======================

    webapp.mapper.connect( '/api/tools/all_requirements', action='all_requirements', controller="tools" )
    webapp.mapper.connect( '/api/tools/{id:.+?}/build', action='build', controller="tools" )
    webapp.mapper.connect( '/api/tools/{id:.+?}/reload', action='reload', controller="tools" )
    webapp.mapper.connect( '/api/tools/{id:.+?}/diagnostics', action='diagnostics', controller="tools" )
    webapp.mapper.connect( '/api/tools/{id:.+?}/citations', action='citations', controller="tools" )
    webapp.mapper.connect( '/api/tools/{id:.+?}/download', action='download', controller="tools" )
    webapp.mapper.connect( '/api/tools/{id:.+?}/requirements', action='requirements', controller="tools")
    webapp.mapper.connect( '/api/tools/{id:.+?}/install_dependencies', action='install_dependencies', controller="tools", conditions=dict( method=[ "POST" ] ))
    webapp.mapper.connect( '/api/tools/{id:.+?}/build_dependency_cache', action='build_dependency_cache', controller="tools", conditions=dict( method=[ "POST" ] ))
    webapp.mapper.connect( '/api/tools/{id:.+?}', action='show', controller="tools" )
    webapp.mapper.resource( 'tool', 'tools', path_prefix='/api' )

    webapp.mapper.connect( '/api/dependency_resolvers/clean', action="clean", controller="tool_dependencies", conditions=dict( method=[ "POST" ]) )
    webapp.mapper.connect( '/api/dependency_resolvers/dependency', action="manager_dependency", controller="tool_dependencies", conditions=dict( method=[ "GET" ] ) )
    webapp.mapper.connect( '/api/dependency_resolvers/dependency', action="install_dependency", controller="tool_dependencies", conditions=dict( method=[ "POST" ] ) )
    webapp.mapper.connect( '/api/dependency_resolvers/requirements', action="manager_requirements", controller="tool_dependencies" )
    webapp.mapper.connect( '/api/dependency_resolvers/{id}/clean', action="clean", controller="tool_dependencies", conditions=dict( method=[ "POST" ]) )
    webapp.mapper.connect( '/api/dependency_resolvers/{id}/dependency', action="resolver_dependency", controller="tool_dependencies", conditions=dict( method=[ "GET" ] ) )
    webapp.mapper.connect( '/api/dependency_resolvers/{id}/dependency', action="install_dependency", controller="tool_dependencies", conditions=dict( method=[ "POST" ] ) )
    webapp.mapper.connect( '/api/dependency_resolvers/{id}/requirements', action="resolver_requirements", controller="tool_dependencies" )
    webapp.mapper.resource( 'dependency_resolver', 'dependency_resolvers', controller="tool_dependencies", path_prefix='api' )

    webapp.mapper.resource_with_deleted( 'user', 'users', path_prefix='/api' )
    webapp.mapper.resource( 'genome', 'genomes', path_prefix='/api' )
    webapp.mapper.connect( '/api/genomes/{id}/indexes', controller='genomes', action='indexes' )
    webapp.mapper.connect( '/api/genomes/{id}/sequences', controller='genomes', action='sequences' )
    webapp.mapper.resource( 'visualization', 'visualizations', path_prefix='/api' )
    webapp.mapper.connect( '/api/workflows/build_module', action='build_module', controller="workflows" )
    webapp.mapper.resource( 'workflow', 'workflows', path_prefix='/api' )
    webapp.mapper.resource_with_deleted( 'history', 'histories', path_prefix='/api' )
    webapp.mapper.connect( '/api/histories/{history_id}/citations', action='citations', controller="histories" )
    webapp.mapper.connect(
        'dynamic_tool_confs',
        '/api/configuration/dynamic_tool_confs',
        controller="configuration",
        action="dynamic_tool_confs"
    )
    webapp.mapper.connect(
        'tool_lineages',
        '/api/configuration/tool_lineages',
        controller="configuration",
        action="tool_lineages"
    )
    webapp.mapper.connect(
        '/api/configuration/toolbox',
        controller="configuration",
        action="reload_toolbox",
        conditions=dict( method=["PUT"] )
    )
    webapp.mapper.resource( 'configuration', 'configuration', path_prefix='/api' )
    webapp.mapper.connect( "configuration_version",
                           "/api/version", controller="configuration",
                           action="version", conditions=dict( method=[ "GET" ] ) )
    webapp.mapper.connect( "api_whoami",
                           "/api/whoami", controller='configuration',
                           action='whoami',
                           conditions=dict( method=[ "GET" ] ) )
    webapp.mapper.resource( 'datatype',
                            'datatypes',
                            path_prefix='/api',
                            collection={ 'sniffers': 'GET', 'mapping': 'GET', 'converters': 'GET', 'edam_data': 'GET', 'edam_formats': 'GET' },
                            parent_resources=dict( member_name='datatype', collection_name='datatypes' ) )
    webapp.mapper.resource( 'search', 'search', path_prefix='/api' )
    webapp.mapper.resource( 'page', 'pages', path_prefix="/api")
    webapp.mapper.resource( 'revision', 'revisions',
                            path_prefix='/api/pages/{page_id}',
                            controller='page_revisions',
                            parent_resources=dict( member_name='page', collection_name='pages' ) )

    webapp.mapper.connect( "history_archive_export",
                           "/api/histories/{id}/exports", controller="histories",
                           action="archive_export", conditions=dict( method=[ "PUT" ] ) )
    webapp.mapper.connect( "history_archive_download",
                           "/api/histories/{id}/exports/{jeha_id}", controller="histories",
                           action="archive_download", conditions=dict( method=[ "GET" ] ) )

    # ---- visualizations registry ---- generic template renderer
    # @deprecated: this route should be considered deprecated
    webapp.add_route( '/visualization/show/{visualization_name}', controller='visualization', action='render', visualization_name=None )

    # provide an alternate route to visualization plugins that's closer to their static assets
    # (/plugins/visualizations/{visualization_name}/static) and allow them to use relative urls to those
    webapp.mapper.connect( 'visualization_plugin', '/plugins/visualizations/{visualization_name}/show',
        controller='visualization', action='render' )
    webapp.mapper.connect( 'saved_visualization', '/plugins/visualizations/{visualization_name}/saved',
        controller='visualization', action='saved' )
    # same with IE's
    webapp.mapper.connect( 'interactive_environment_plugin', '/plugins/interactive_environments/{visualization_name}/show',
        controller='visualization', action='render' )
    webapp.mapper.connect( 'saved_interactive_environment', '/plugins/interactive_environments/{visualization_name}/saved',
        controller='visualization', action='saved' )

    # Deprecated in favor of POST /api/workflows with 'workflow' in payload.
    webapp.mapper.connect( 'import_workflow_deprecated',
                           '/api/workflows/upload',
                           controller='workflows',
                           action='import_new_workflow_deprecated',
                           conditions=dict( method=['POST'] ) )
    webapp.mapper.connect( 'workflow_dict',
                           '/api/workflows/{workflow_id}/download',
                           controller='workflows',
                           action='workflow_dict',
                           conditions=dict( method=['GET'] ) )
    # Preserve the following download route for now for dependent applications  -- deprecate at some point
    webapp.mapper.connect( 'workflow_dict',
                           '/api/workflows/download/{workflow_id}',
                           controller='workflows',
                           action='workflow_dict',
                           conditions=dict( method=['GET'] ) )
    # Deprecated in favor of POST /api/workflows with shared_workflow_id in payload.
    webapp.mapper.connect( 'import_shared_workflow_deprecated',
                           '/api/workflows/import',
                           controller='workflows',
                           action='import_shared_workflow_deprecated',
                           conditions=dict( method=['POST'] ) )

    # route for creating/getting converted datasets
    webapp.mapper.connect( '/api/datasets/{dataset_id}/converted', controller='datasets', action='converted', ext=None )
    webapp.mapper.connect( '/api/datasets/{dataset_id}/converted/{ext}', controller='datasets', action='converted' )

    # API refers to usages and invocations - these mean the same thing but the
    # usage routes should be considered deprecated.
    invoke_names = {
        "invocations": "",
        "usage": "_deprecated",
    }
    for noun, suffix in invoke_names.iteritems():
        name = "%s%s" % (noun, suffix)
        webapp.mapper.connect(
            'list_workflow_%s' % name,
            '/api/workflows/{workflow_id}/%s' % noun,
            controller='workflows',
            action='index_invocations',
            conditions=dict(method=['GET'])
        )

        webapp.mapper.connect(
            'workflow_%s_contents' % name,
            '/api/workflows/{workflow_id}/%s/{invocation_id}' % noun,
            controller='workflows',
            action='show_invocation',
            conditions=dict(method=['GET'])
        )

        webapp.mapper.connect(
            'cancel_workflow_%s' % name,
            '/api/workflows/{workflow_id}/%s/{invocation_id}' % noun,
            controller='workflows',
            action='cancel_invocation',
            conditions=dict(method=['DELETE'])
        )

        webapp.mapper.connect(
            'workflow_%s_step' % name,
            '/api/workflows/{workflow_id}/%s/{invocation_id}/steps/{step_id}' % noun,
            controller='workflows',
            action='invocation_step',
            conditions=dict(method=['GET'])
        )

        webapp.mapper.connect(
            'workflow_%s_step_update' % name,
            '/api/workflows/{workflow_id}/%s/{invocation_id}/steps/{step_id}' % noun,
            controller='workflows',
            action='update_invocation_step',
            conditions=dict(method=['PUT'])
        )

        webapp.mapper.connect(
            'workflow_%s' % name,
            '/api/workflows/{workflow_id}/%s' % noun,
            controller='workflows',
            action='invoke',
            conditions=dict( method=['POST'] )
        )
    # ============================
    # ===== AUTHENTICATE API =====
    # ============================

    webapp.mapper.connect( 'api_key_retrieval',
                           '/api/authenticate/baseauth/',
                           controller='authenticate',
                           action='get_api_key',
                           conditions=dict( method=[ "GET" ] ) )

    # =====================
    # ===== TOURS API =====
    # =====================

    webapp.mapper.connect( 'index',
                           '/api/tours',
                           controller='tours',
                           action='index',
                           conditions=dict( method=["GET"] ) )

    webapp.mapper.connect( 'show',
                           '/api/tours/{tour_id}',
                           controller='tours',
                           action='show',
                           conditions=dict( method=[ "GET" ] ) )

    webapp.mapper.connect( 'update_tour',
                           '/api/tours/{tour_id}',
                           controller='tours',
                           action='update_tour',
                           conditions=dict( method=[ "POST" ] ) )

    # ================================
    # ===== USERS API =====
    # ================================

    webapp.mapper.connect( 'api_key',
                           '/api/users/{id}/api_key',
                           controller='users',
                           action='api_key',
                           conditions=dict( method=["POST"] ) )

    webapp.mapper.connect( 'get_api_key',
                           '/api/users/{id}/api_key/inputs',
                           controller='users',
                           action='get_api_key',
                           conditions=dict( method=["GET"] ) )

    webapp.mapper.connect( 'set_api_key',
                           '/api/users/{id}/api_key/inputs',
                           controller='users',
                           action='set_api_key',
                           conditions=dict( method=["PUT"] ) )

    webapp.mapper.connect( 'get_information',
                           '/api/users/{id}/information/inputs',
                           controller='users',
                           action='get_information',
                           conditions=dict( method=["GET"] ) )

    webapp.mapper.connect( 'set_information',
                           '/api/users/{id}/information/inputs',
                           controller='users',
                           action='set_information',
                           conditions=dict( method=["PUT"] ) )

    webapp.mapper.connect( 'get_password',
                           '/api/users/{id}/password/inputs',
                           controller='users',
                           action='get_password',
                           conditions=dict( method=["GET"] ) )

    webapp.mapper.connect( 'set_password',
                           '/api/users/{id}/password/inputs',
                           controller='users',
                           action='set_password',
                           conditions=dict( method=["PUT"] ) )

    webapp.mapper.connect( 'get_permissions',
                           '/api/users/{id}/permissions/inputs',
                           controller='users',
                           action='get_permissions',
                           conditions=dict( method=["GET"] ) )

    webapp.mapper.connect( 'set_permissions',
                           '/api/users/{id}/permissions/inputs',
                           controller='users',
                           action='set_permissions',
                           conditions=dict( method=["PUT"] ) )

    webapp.mapper.connect( 'get_toolbox_filters',
                           '/api/users/{id}/toolbox_filters/inputs',
                           controller='users',
                           action='get_toolbox_filters',
                           conditions=dict( method=["GET"] ) )

    webapp.mapper.connect( 'set_toolbox_filters',
                           '/api/users/{id}/toolbox_filters/inputs',
                           controller='users',
                           action='set_toolbox_filters',
                           conditions=dict( method=["PUT"] ) )

    webapp.mapper.connect( 'get_communication',
                           '/api/users/{id}/communication/inputs',
                           controller='users',
                           action='get_communication',
                           conditions=dict( method=["GET"] ) )

    webapp.mapper.connect( 'set_communication',
                           '/api/users/{id}/communication/inputs',
                           controller='users',
                           action='set_communication',
                           conditions=dict( method=["PUT"] ) )

    # ========================
    # ===== WEBHOOKS API =====
    # ========================

    webapp.mapper.connect( 'get_all',
                           '/api/webhooks',
                           controller='webhooks',
                           action='get_all',
                           conditions=dict( method=[ "GET" ] ) )

    webapp.mapper.connect( 'get_random',
                           '/api/webhooks/{webhook_type}',
                           controller='webhooks',
                           action='get_random',
                           conditions=dict( method=[ "GET" ] ) )

    webapp.mapper.connect( 'get_all_by_type',
                           '/api/webhooks/{webhook_type}/all',
                           controller='webhooks',
                           action='get_all_by_type',
                           conditions=dict( method=[ "GET" ] ) )

    webapp.mapper.connect( 'get_data',
                           '/api/webhooks/{webhook_name}/get_data',
                           controller='webhooks',
                           action='get_data',
                           conditions=dict( method=[ "GET" ] ) )

    # =======================
    # ===== LIBRARY API =====
    # =======================

    webapp.mapper.connect( 'update_library',
                           '/api/libraries/{id}',
                           controller='libraries',
                           action='update',
                           conditions=dict( method=[ "PATCH", "PUT" ] ) )

    webapp.mapper.connect( 'show_library_permissions',
                           '/api/libraries/{encoded_library_id}/permissions',
                           controller='libraries',
                           action='get_permissions',
                           conditions=dict( method=[ "GET" ] ) )

    webapp.mapper.connect( 'set_library_permissions',
                           '/api/libraries/{encoded_library_id}/permissions',
                           controller='libraries',
                           action='set_permissions',
                           conditions=dict( method=[ "POST" ] ) )

    webapp.mapper.connect( 'show_ld_item',
                           '/api/libraries/datasets/{id}',
                           controller='lda_datasets',
                           action='show',
                           conditions=dict( method=[ "GET" ] ) )

    webapp.mapper.connect( 'load_ld',
                           '/api/libraries/datasets/',
                           controller='lda_datasets',
                           action='load',
                           conditions=dict( method=[ "POST" ] ) )

    webapp.mapper.connect( 'show_version_of_ld_item',
                           '/api/libraries/datasets/{encoded_dataset_id}/versions/{encoded_ldda_id}',
                           controller='lda_datasets',
                           action='show_version',
                           conditions=dict( method=[ "GET" ] ) )

    webapp.mapper.connect( 'show_legitimate_lda_roles',
                           '/api/libraries/datasets/{encoded_dataset_id}/permissions',
                           controller='lda_datasets',
                           action='show_roles',
                           conditions=dict( method=[ "GET" ] ) )

    webapp.mapper.connect( 'update_lda_permissions',
                           '/api/libraries/datasets/{encoded_dataset_id}/permissions',
                           controller='lda_datasets',
                           action='update_permissions',
                           conditions=dict( method=[ "POST" ] ) )

    webapp.mapper.connect( 'delete_lda_item',
                           '/api/libraries/datasets/{encoded_dataset_id}',
                           controller='lda_datasets',
                           action='delete',
                           conditions=dict( method=[ "DELETE" ] ) )

    webapp.mapper.connect( 'download_lda_items',
                           '/api/libraries/datasets/download/{format}',
                           controller='lda_datasets',
                           action='download',
                           conditions=dict( method=[ "POST", "GET" ] ) )

    webapp.mapper.resource_with_deleted( 'library',
                                         'libraries',
                                         path_prefix='/api' )

    webapp.mapper.resource( 'content',
                            'contents',
                            controller='library_contents',
                            name_prefix='library_',
                            path_prefix='/api/libraries/{library_id}',
                            parent_resources=dict( member_name='library', collection_name='libraries' ) )

    _add_item_extended_metadata_controller( webapp,
                                            name_prefix="library_dataset_",
                                            path_prefix='/api/libraries/{library_id}/contents/{library_content_id}' )

    # =======================
    # ===== FOLDERS API =====
    # =======================

    webapp.mapper.connect( 'add_history_datasets_to_library',
                           '/api/folders/{encoded_folder_id}/contents',
                           controller='folder_contents',
                           action='create',
                           conditions=dict( method=[ "POST" ] ) )

    webapp.mapper.connect( 'create_folder',
                           '/api/folders/{encoded_parent_folder_id}',
                           controller='folders',
                           action='create',
                           conditions=dict( method=[ "POST" ] ) )

    webapp.mapper.connect( 'delete_folder',
                           '/api/folders/{encoded_folder_id}',
                           controller='folders',
                           action='delete',
                           conditions=dict( method=[ "DELETE" ] ) )

    webapp.mapper.connect( 'update_folder',
                           '/api/folders/{encoded_folder_id}',
                           controller='folders',
                           action='update',
                           conditions=dict( method=[ "PATCH", "PUT" ] ) )

    webapp.mapper.resource( 'folder',
                            'folders',
                            path_prefix='/api' )

    webapp.mapper.connect( 'show_folder_permissions',
                           '/api/folders/{encoded_folder_id}/permissions',
                           controller='folders',
                           action='get_permissions',
                           conditions=dict( method=[ "GET" ] ) )

    webapp.mapper.connect( 'set_folder_permissions',
                           '/api/folders/{encoded_folder_id}/permissions',
                           controller='folders',
                           action='set_permissions',
                           conditions=dict( method=[ "POST" ] ) )

    webapp.mapper.resource( 'content',
                            'contents',
                            controller='folder_contents',
                            name_prefix='folder_',
                            path_prefix='/api/folders/{folder_id}',
                            parent_resources=dict( member_name='folder', collection_name='folders' ),
                            conditions=dict( method=[ "GET" ] )  )

    webapp.mapper.resource( 'job',
                            'jobs',
                            path_prefix='/api' )
    webapp.mapper.connect( 'job_search', '/api/jobs/search', controller='jobs', action='search', conditions=dict( method=['POST'] ) )
    webapp.mapper.connect( 'job_inputs', '/api/jobs/{id}/inputs', controller='jobs', action='inputs', conditions=dict( method=['GET'] ) )
    webapp.mapper.connect( 'job_outputs', '/api/jobs/{id}/outputs', controller='jobs', action='outputs', conditions=dict( method=['GET'] ) )
    webapp.mapper.connect( 'build_for_rerun', '/api/jobs/{id}/build_for_rerun', controller='jobs', action='build_for_rerun', conditions=dict( method=['GET'] ) )

    # Job files controllers. Only for consumption by remote job runners.
    webapp.mapper.resource( 'file',
                            'files',
                            controller="job_files",
                            name_prefix="job_",
                            path_prefix='/api/jobs/{job_id}',
                            parent_resources=dict( member_name="job", collection_name="jobs" ) )

    _add_item_extended_metadata_controller( webapp,
                                            name_prefix="history_dataset_",
                                            path_prefix='/api/histories/{history_id}/contents/{history_content_id}' )

    # ====================
    # ===== TOOLSHED =====
    # ====================

    # Handle displaying tool help images and README file images contained in repositories installed from the tool shed.
    webapp.add_route( '/admin_toolshed/static/images/{repository_id}/{image_file:.+?}',
                      controller='admin_toolshed',
                      action='display_image_in_repository',
                      repository_id=None,
                      image_file=None )

    webapp.mapper.connect( 'shed_category',
                           '/api/tool_shed_repositories/shed_category',
                           controller='tool_shed_repositories',
                           action='shed_category',
                           conditions=dict( method=[ "GET" ] ) )

    webapp.mapper.connect( 'shed_repository',
                           '/api/tool_shed_repositories/shed_repository',
                           controller='tool_shed_repositories',
                           action='shed_repository',
                           conditions=dict( method=[ "GET" ] ) )

    webapp.mapper.connect( 'shed_categories',
                           '/api/tool_shed_repositories/shed_categories',
                           controller='tool_shed_repositories',
                           action='shed_categories',
                           conditions=dict( method=[ "GET" ] ) )

    webapp.mapper.connect( 'tool_shed_repository',
                           '/api/tool_shed_repositories/:id/status',
                           controller='tool_shed_repositories',
                           action='status',
                           conditions=dict( method=[ "GET" ] ) )

    webapp.mapper.connect( 'install_repository',
                           '/api/tool_shed_repositories/install',
                           controller='tool_shed_repositories',
                           action='install',
                           conditions=dict( method=[ 'POST' ] ) )

    # Galaxy API for tool shed features.
    webapp.mapper.resource( 'tool_shed_repository',
                            'tool_shed_repositories',
                            member={ 'repair_repository_revision': 'POST',
                                     'exported_workflows': 'GET',
                                     'import_workflow': 'POST',
                                     'import_workflows': 'POST' },
                            collection={ 'get_latest_installable_revision': 'POST',
                                         'reset_metadata_on_installed_repositories': 'POST' },
                            controller='tool_shed_repositories',
                            name_prefix='tool_shed_repository_',
                            path_prefix='/api',
                            new={ 'install_repository_revision': 'POST' },
                            parent_resources=dict( member_name='tool_shed_repository', collection_name='tool_shed_repositories' ) )

    # ==== Trace/Metrics Logger
    # Connect logger from app
    if app.trace_logger:
        webapp.trace_logger = app.trace_logger

    # metrics logging API
    # webapp.mapper.connect( "index", "/api/metrics",
    #    controller="metrics", action="index", conditions=dict( method=["GET"] ) )
    # webapp.mapper.connect( "show", "/api/metrics/{id}",
    #    controller="metrics", action="show", conditions=dict( method=["GET"] ) )
    webapp.mapper.connect( "create", "/api/metrics", controller="metrics",
                           action="create", conditions=dict( method=["POST"] ) )


def _add_item_tags_controller( webapp, name_prefix, path_prefix, **kwd ):
    # Not just using map.resources because actions should be based on name not id
    controller = "%stags" % name_prefix
    name = "%stag" % name_prefix
    path = "%s/tags" % path_prefix
    map = webapp.mapper
    # Allow view items' tags.
    map.connect(name, path,
                controller=controller, action="index",
                conditions=dict(method=["GET"]))
    # Allow remove tag from item
    map.connect("%s_delete" % name, "%s/tags/{tag_name}" % path_prefix,
                controller=controller, action="delete",
                conditions=dict(method=["DELETE"]))
    # Allow create a new tag with from name
    map.connect("%s_create" % name, "%s/tags/{tag_name}" % path_prefix,
                controller=controller, action="create",
                conditions=dict(method=["POST"]))
    # Allow update tag value
    map.connect("%s_update" % name, "%s/tags/{tag_name}" % path_prefix,
                controller=controller, action="update",
                conditions=dict(method=["PUT"]))
    # Allow show tag by name
    map.connect("%s_show" % name, "%s/tags/{tag_name}" % path_prefix,
                controller=controller, action="show",
                conditions=dict(method=["GET"]))


def _add_item_extended_metadata_controller( webapp, name_prefix, path_prefix, **kwd ):
    controller = "%sextended_metadata" % name_prefix
    name = "%sextended_metadata" % name_prefix
    webapp.mapper.resource(name, "extended_metadata", path_prefix=path_prefix, controller=controller)


def _add_item_annotation_controller( webapp, name_prefix, path_prefix, **kwd ):
    controller = "%sannotations" % name_prefix
    name = "%sannotation" % name_prefix
    webapp.mapper.resource(name, "annotation", path_prefix=path_prefix, controller=controller)


def _add_item_provenance_controller( webapp, name_prefix, path_prefix, **kwd ):
    controller = "%sprovenance" % name_prefix
    name = "%sprovenance" % name_prefix
    webapp.mapper.resource(name, "provenance", path_prefix=path_prefix, controller=controller)


def wrap_in_middleware( app, global_conf, **local_conf ):
    """
    Based on the configuration wrap `app` in a set of common and useful
    middleware.
    """
    webapp = app

    # Merge the global and local configurations
    conf = global_conf.copy()
    conf.update(local_conf)
    debug = asbool( conf.get( 'debug', False ) )
    # First put into place httpexceptions, which must be most closely
    # wrapped around the application (it can interact poorly with
    # other middleware):
    app = httpexceptions.make_middleware( app, conf )
    log.debug( "Enabling 'httpexceptions' middleware" )
    # Statsd request timing and profiling
    statsd_host = conf.get('statsd_host', None)
    if statsd_host:
        from galaxy.web.framework.middleware.statsd import StatsdMiddleware
        app = StatsdMiddleware( app,
                                statsd_host,
                                conf.get('statsd_port', 8125),
                                conf.get('statsd_prefix', 'galaxy') )
        log.debug( "Enabling 'statsd' middleware" )
    # If we're using remote_user authentication, add middleware that
    # protects Galaxy from improperly configured authentication in the
    # upstream server
    single_user = conf.get( 'single_user', None )
    use_remote_user = asbool(conf.get( 'use_remote_user', False )) or single_user
    if use_remote_user:
        from galaxy.web.framework.middleware.remoteuser import RemoteUser
        app = RemoteUser( app, maildomain=conf.get( 'remote_user_maildomain', None ),
                          display_servers=util.listify( conf.get( 'display_servers', '' ) ),
                          single_user=single_user,
                          admin_users=conf.get( 'admin_users', '' ).split( ',' ),
                          remote_user_header=conf.get( 'remote_user_header', 'HTTP_REMOTE_USER' ),
                          remote_user_secret_header=conf.get('remote_user_secret', None),
                          normalize_remote_user_email=conf.get('normalize_remote_user_email', False))
    # The recursive middleware allows for including requests in other
    # requests or forwarding of requests, all on the server side.
    if asbool(conf.get('use_recursive', True)):
        from paste import recursive
        app = recursive.RecursiveMiddleware( app, conf )
        log.debug( "Enabling 'recursive' middleware" )
    # If sentry logging is enabled, log here before propogating up to
    # the error middleware
    sentry_dsn = conf.get( 'sentry_dsn', None )
    if sentry_dsn:
        from galaxy.web.framework.middleware.sentry import Sentry
        app = Sentry( app, sentry_dsn )
    # Various debug middleware that can only be turned on if the debug
    # flag is set, either because they are insecure or greatly hurt
    # performance
    if debug:
        # Middleware to check for WSGI compliance
        if asbool( conf.get( 'use_lint', False ) ):
            from paste import lint
            app = lint.make_middleware( app, conf )
            log.debug( "Enabling 'lint' middleware" )
        # Middleware to run the python profiler on each request
        if asbool( conf.get( 'use_profile', False ) ):
            from paste.debug import profile
            app = profile.ProfileMiddleware( app, conf )
            log.debug( "Enabling 'profile' middleware" )
    if debug and asbool( conf.get( 'use_interactive', False ) ) and not process_is_uwsgi:
        # Interactive exception debugging, scary dangerous if publicly
        # accessible, if not enabled we'll use the regular error printing
        # middleware.
        from weberror import evalexception
        app = evalexception.EvalException( app, conf,
                                           templating_formatters=build_template_error_formatters() )
        log.debug( "Enabling 'eval exceptions' middleware" )
    else:
        if debug and asbool( conf.get( 'use_interactive', False ) ) and process_is_uwsgi:
            log.error("Interactive debugging middleware is enabled in your configuration "
                      "but this is a uwsgi process.  Refusing to wrap in interactive error middleware.")
        # Not in interactive debug mode, just use the regular error middleware
        import galaxy.web.framework.middleware.error
        app = galaxy.web.framework.middleware.error.ErrorMiddleware( app, conf )
        log.debug( "Enabling 'error' middleware" )
    # Transaction logging (apache access.log style)
    if asbool( conf.get( 'use_translogger', True ) ):
        from galaxy.web.framework.middleware.translogger import TransLogger
        app = TransLogger( app )
        log.debug( "Enabling 'trans logger' middleware" )
    # X-Forwarded-Host handling
    from galaxy.web.framework.middleware.xforwardedhost import XForwardedHostMiddleware
    app = XForwardedHostMiddleware( app )
    log.debug( "Enabling 'x-forwarded-host' middleware" )
    # Request ID middleware
    from galaxy.web.framework.middleware.request_id import RequestIDMiddleware
    app = RequestIDMiddleware( app )
    log.debug( "Enabling 'Request ID' middleware" )

    # api batch call processing middleware
    from galaxy.web.framework.middleware.batch import BatchMiddleware
    app = BatchMiddleware( webapp, app, {})
    log.debug( "Enabling 'Batch' middleware" )

    return app


def wrap_in_static( app, global_conf, plugin_frameworks=None, **local_conf ):
    from galaxy.web.framework.middleware.static import CacheableStaticURLParser as Static
    urlmap, cache_time = galaxy.web.framework.webapp.build_url_map( app, global_conf, local_conf )
    # wrap any static dirs for plugins
    plugin_frameworks = plugin_frameworks or []
    for framework in plugin_frameworks:
        if framework and framework.serves_static:
            # invert control to each plugin for finding their own static dirs
            for plugin_url, plugin_static_path in framework.get_static_urls_and_paths():
                plugin_url = '/plugins/' + plugin_url
                urlmap[( plugin_url )] = Static( plugin_static_path, cache_time )
                log.debug( 'added url, path to static middleware: %s, %s', plugin_url, plugin_static_path )

    # URL mapper becomes the root webapp
    return urlmap
