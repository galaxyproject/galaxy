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
            'support_url'               : app.config.get("support_url", "https://wiki.galaxyproject.org/Support"),
            'search_url'                : app.config.get("search_url", "http://galaxyproject.org/search/usegalaxy/"),
            'mailing_lists'             : app.config.get("mailing_lists", "https://wiki.galaxyproject.org/MailingLists"),
            'screencasts_url'           : app.config.get("screencasts_url", "https://vimeo.com/galaxyproject"),
            'wiki_url'                  : app.config.get("wiki_url", "https://wiki.galaxyproject.org/"),
            'citation_url'              : app.config.get("citation_url", "https://wiki.galaxyproject.org/CitingGalaxy"),
            'terms_url'                 : app.config.get("terms_url", ""),
            'allow_user_creation'       : app.config.allow_user_creation,
            'logo_url'                  : h.url_for(app.config.get( 'logo_url', '/')),
            'logo_src'                  : h.url_for( app.config.get( 'logo_src', '/static/images/galaxyIcon_noText.png' ) ),
            'is_admin_user'             : trans.user_is_admin(),
            'active_view'               : active_view,
            'ftp_upload_dir'            : app.config.get("ftp_upload_dir",  None),
            'ftp_upload_site'           : app.config.get("ftp_upload_site",  None),
            'datatypes_disable_auto'    : app.config.get_bool("datatypes_disable_auto",  False),
            'user_requests'             : bool( trans.user and ( trans.user.requests or app.security_agent.get_accessible_request_types( trans, trans.user ) ) ),
            'user_json'                 : get_user_dict()
        }
    %>

    ## load the frame manager
    <script type="text/javascript">
        if( !window.Galaxy ){
            Galaxy = {};
        }

        // if we're in an iframe, create styles that hide masthead/messagebox, and reset top for panels
        // note: don't use a link to avoid roundtrip request
        // note: we can't select here because the page (incl. messgaebox, center, etc.) isn't fully rendered
        // TODO: remove these when we no longer navigate with iframes
        var in_iframe = window !== window.top;
        if( in_iframe ){
            var styleElement = document.createElement( 'style' );
            document.head.appendChild( styleElement );
            [
                '#masthead, #messagebox { display: none; }',
                '#center, #right, #left { top: 0 !important; }',
             ].forEach( function( rule ){
                styleElement.sheet.insertRule( rule, 0 );
            });
        }
        // TODO: ?? move above to base_panels.mako?

        ## load galaxy js-modules
        require([
            'layout/masthead',
            'mvc/ui/ui-modal',
            'mvc/user/user-model'
        ], function( Masthead, Modal, user ){
            if( !Galaxy.user ) {
                // this doesn't need to wait for the page being readied
                Galaxy.user = new user.User(${ h.dumps( masthead_config[ 'user_json' ], indent=2 ) });
            }

            $(function() {
                if (!Galaxy.masthead) {
                    Galaxy.masthead = new Masthead.View(${ h.dumps( masthead_config ) });
                    Galaxy.modal = new Modal.View();
                    $('#masthead').replaceWith( Galaxy.masthead.render().$el );
                }
            });
        });
    </script>
</%def>