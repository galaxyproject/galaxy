<%inherit file="/base.mako"/>
<%namespace file="/galaxy_client_app.mako" import="get_user_dict" />
${h.js("libs/bibtex", "libs/jquery/jquery-ui")}
${h.css("jquery-ui/smoothness/jquery-ui")}
${h.css("base")}
<%def name="title()">Galaxy</%def>
<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.templates("tool_link", "panel_section", "tool_search")}
</%def>
<%
    ## get configuration
    from markupsafe import escape
    app = trans.app
    app_config = {
        'active_view'                   : 'analysis',
        'params'                        : dict( trans.request.params ),
        'brand'                         : app.config.get("brand", ""),
        'nginx_upload_path'             : app.config.get("nginx_upload_path", h.url_for(controller='api', action='tools')),
        'use_remote_user'               : app.config.use_remote_user,
        'remote_user_logout_href'       : app.config.remote_user_logout_href,
        'enable_cloud_launch'           : app.config.get_bool('enable_cloud_launch', False),
        'lims_doc_url'                  : app.config.get("lims_doc_url", "https://usegalaxy.org/u/rkchak/p/sts"),
        'biostar_url'                   : app.config.biostar_url,
        'biostar_url_redirect'          : h.url_for( controller='biostar', action='biostar_redirect', qualified=True ),
        'support_url'                   : app.config.get("support_url", "https://wiki.galaxyproject.org/Support"),
        'search_url'                    : app.config.get("search_url", "http://galaxyproject.org/search/usegalaxy/"),
        'mailing_lists'                 : app.config.get("mailing_lists", "https://wiki.galaxyproject.org/MailingLists"),
        'screencasts_url'               : app.config.get("screencasts_url", "https://vimeo.com/galaxyproject"),
        'wiki_url'                      : app.config.get("wiki_url", "https://wiki.galaxyproject.org/"),
        'citation_url'                  : app.config.get("citation_url", "https://wiki.galaxyproject.org/CitingGalaxy"),
        'terms_url'                     : app.config.get("terms_url", ""),
        'allow_user_creation'           : app.config.allow_user_creation,
        'logo_url'                      : h.url_for(app.config.get( 'logo_url', '/')),
        'spinner_url'                   : h.url_for('/static/images/loading_small_white_bg.gif'),
        'search_url'                    : h.url_for(controller='root', action='tool_search'),
        'is_admin_user'                 : trans.user_is_admin(),
        'ftp_upload_dir'                : app.config.get("ftp_upload_dir",  None),
        'ftp_upload_site'               : app.config.get("ftp_upload_site",  None),
        'datatypes_disable_auto'        : app.config.get_bool("datatypes_disable_auto",  False),
        'toolbox'                       : app.toolbox.to_dict( trans, in_panel=False ),
        'toolbox_in_panel'              : app.toolbox.to_dict( trans ),
        'message_box_visible'           : app.config.message_box_visible,
        'show_inactivity_warning'       : trans.user and ( ( trans.user.active is False ) and ( app.config.user_activation_on ) and ( app.config.inactivity_box_content is not None ) ),
        'user_requests'                 : bool( trans.user and ( trans.user.requests or app.security_agent.get_accessible_request_types( trans, trans.user ) ) ),
        'stored_workflow_menu_entries'  : []
    }
    if hasattr( trans.user, 'stored_workflow_menu_entries' ):
        for m in trans.user.stored_workflow_menu_entries:
            app_config[ 'stored_workflow_menu_entries' ].append({
                'encoded_stored_workflow_id' : trans.security.encode_id( m.stored_workflow_id ),
                'stored_workflow' : {
                    'name' : util.unicodify( m.stored_workflow.name )
                }
            })
%>
<script>
    require(['mvc/app/app-view'], function( App ){
        $( function() {
            var app = new App( ${ h.dumps( app_config ) } );
        } );
    });

    %if app.config.ga_code:
          (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
          (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
          m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
          })(window,document,'script','//www.google-analytics.com/analytics.js','ga');
          ga('create', '${app.config.ga_code}', 'auto');
          ga('send', 'pageview');
    %endif
</script>
