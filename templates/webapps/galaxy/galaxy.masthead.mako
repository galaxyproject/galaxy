<%namespace file="/galaxy_client_app.mako" import="get_user_dict" />

## masthead head generator
<%def name="load(active_view = None)">
    <%
        from markupsafe import escape
        ## get configuration
        masthead_config = {
            ## inject configuration
            'brand'                     : app.config.brand or '',
            'display_galaxy_brand'      : app.config.display_galaxy_brand,
            'nginx_upload_path'         : app.config.nginx_upload_path or h.url_for(controller='api', action='tools'),
            'use_remote_user'           : app.config.use_remote_user,
            'remote_user_logout_href'   : app.config.remote_user_logout_href,
            'lims_doc_url'              : app.config.get("lims_doc_url", "https://usegalaxy.org/u/rkchak/p/sts"),
            'default_locale'            : app.config.default_locale,
            'support_url'               : app.config.support_url,
            'screencasts_url'           : app.config.screencasts_url,
            'wiki_url'                  : app.config.wiki_url,
            'citation_url'              : app.config.citation_url,
            'release_doc_base_url'      : app.config.release_doc_base_url,
            'terms_url'                 : app.config.terms_url or '',
            'allow_user_creation'       : app.config.allow_user_creation,
            'logo_url'                  : h.url_for(app.config.logo_url),
            'logo_src'                  : h.url_for(app.config.get('logo_src', '/static/favicon.png')),
            'logo_src_secondary'        : h.url_for(app.config.get('logo_src_secondary')) if app.config.get('logo_src_secondary') else None,
            'is_admin_user'             : trans.user_is_admin,
            'active_view'               : active_view,
            'ftp_upload_site'           : app.config.ftp_upload_site,
            'datatypes_disable_auto'    : app.config.datatypes_disable_auto,
            'user_json'                 : get_user_dict()
        }
    %>

    ## load the frame manager
    <script type="text/javascript">
        if (window.self === window.top) {
            config.addInitialization(function (galaxy, config) {
                console.log("galaxy.masthead.mako", "initialize masthead");
                let options = ${h.dumps(masthead_config)};
                const container = document.getElementById("masthead");
                window.bundleEntries.initMasthead(options, container);
            });
        } else {
            console.log("galaxy.masthead.mako", "Detected embedding, not initializing masthead");
            const container = document.getElementById("masthead");
            container.parentNode.removeChild(container);
        }
    </script>
</%def>
