<%namespace file="/galaxy_client_app.mako" import="get_user_dict" />

## masthead head generator
<%def name="load(active_view = None)">
    <%
        from markupsafe import escape
        ## get configuration
        masthead_config = {
            ## inject configuration
            'brand'                     : app.config.get("brand", ""),
            'nginx_upload_path'         : app.config.get("nginx_upload_path", h.url_for(controller='api', action='tools')),
            'use_remote_user'           : app.config.use_remote_user,
            'remote_user_logout_href'   : app.config.remote_user_logout_href,
            'enable_cloud_launch'       : app.config.get_bool('enable_cloud_launch', False),
            'lims_doc_url'              : app.config.get("lims_doc_url", "https://usegalaxy.org/u/rkchak/p/sts"),
            'biostar_url'               : app.config.biostar_url,
            'biostar_url_redirect'      : h.url_for( controller='biostar', action='biostar_redirect', qualified=True ),
            'default_locale'            : app.config.get("default_locale",  "auto"),
            'support_url'               : app.config.get("support_url", "https://galaxyproject.org/support"),
            'search_url'                : app.config.get("search_url", "http://galaxyproject.org/search/"),
            'mailing_lists'             : app.config.get("mailing_lists", "https://galaxyproject.org/mailing-lists"),
            'screencasts_url'           : app.config.get("screencasts_url", "https://vimeo.com/galaxyproject"),
            'wiki_url'                  : app.config.get("wiki_url", "https://galaxyproject.org/"),
            'citation_url'              : app.config.get("citation_url", "https://galaxyproject.org/citing-galaxy"),
            'terms_url'                 : app.config.get("terms_url", ""),
            'allow_user_creation'       : app.config.allow_user_creation,
            'logo_url'                  : h.url_for(app.config.get( 'logo_url', '/')),
            'logo_src'                  : h.url_for( app.config.get( 'logo_src', '/static/images/galaxyIcon_noText.png' ) ),
            'is_admin_user'             : trans.user_is_admin,
            'active_view'               : active_view,
            'ftp_upload_dir'            : app.config.get("ftp_upload_dir",  None),
            'ftp_upload_site'           : app.config.get("ftp_upload_site",  None),
            'datatypes_disable_auto'    : app.config.get_bool("datatypes_disable_auto",  False),
            'user_json'                 : get_user_dict()
        }
    %>

    ## load the frame manager
    <script type="text/javascript">
        config.addInitialization(function(galaxy, config) {
            console.log("galaxy.masthead.mako", "initialize masthead");
            let options = ${h.dumps(masthead_config)};
            let container = document.getElementById("masthead");
            window.bundleEntries.initMasthead(options, container);
        });
    </script>
</%def>
