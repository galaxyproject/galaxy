## get user data
<%def name="get_user_json()">
<%
    """Bootstrapping user API JSON"""
    #TODO: move into common location (poss. BaseController)
    if trans.user:
        user_dict = trans.user.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id,
                                                                             'total_disk_usage': float } )
        user_dict['quota_percent'] = trans.app.quota_agent.get_percent( trans=trans )
    else:
        usage = 0
        percent = None
        try:
            usage = trans.app.quota_agent.get_usage( trans, history=trans.history )
            percent = trans.app.quota_agent.get_percent( trans=trans, usage=usage )
        except AssertionError, assertion:
            # no history for quota_agent.get_usage assertion
            pass
        user_dict = {
            'total_disk_usage'      : int( usage ),
            'nice_total_disk_usage' : util.nice_size( usage ),
            'quota_percent'         : percent
        }
    return user_dict
%>
</%def>

## master head generator
<%def name="load()">
    <%
        ## get configuration
        master_config = {
            ## inject configuration
            'brand'                     : app.config.get("brand", ""),
            'use_remote_user'           : app.config.use_remote_user,
            'remote_user_logout_href'   : app.config.remote_user_logout_href,
            'enable_cloud_launch'       : app.config.get_bool('enable_cloud_launch', False),
            'lims_doc_url'              : app.config.get("lims_doc_url", "http://main.g2.bx.psu.edu/u/rkchak/p/sts"),
            'biostar_url'               : app.config.biostar_url,
            'biostar_url_redirect'      : h.url_for(controller='biostar', action='biostar_redirect', biostar_action='show/tag/galaxy'),
            'support_url'               : app.config.get("support_url", "http://wiki.galaxyproject.org/Support"),
            'search_url'                : app.config.get("search_url", "http://galaxyproject.org/search/usegalaxy/"),
            'mailing_lists'             : app.config.get("mailing_lists", "http://wiki.galaxyproject.org/MailingLists"),
            'screencasts_url'           : app.config.get("screencasts_url", "http://vimeo.com/galaxyproject"),
            'wiki_url'                  : app.config.get("wiki_url", "http://galaxyproject.org/"),
            'citation_url'              : app.config.get("citation_url", "http://wiki.galaxyproject.org/CitingGalaxy"),
            'terms_url'                 : app.config.get("terms_url", ""),
            'allow_user_creation'       : app.config.allow_user_creation,
            'logo_url'                  : h.url_for(app.config.get( 'logo_url', '/')),
            'is_admin_user'             : trans.user and app.config.is_admin_user(trans.user),
            
            ## user details
            'user'          : {
                'requests'  : bool(trans.user and (trans.user.requests or trans.app.security_agent.get_accessible_request_types(trans, trans.user))),
                'email'     : trans.user.email if (trans.user) else "",
                'valid'     : bool(trans.user != None),
                'json'      : get_user_json()
            }
        }
    %>

    ${h.templates( "helpers-common-templates" )}
    ${h.js( "mvc/base-mvc", "utils/localization", "mvc/user/user-model", "mvc/user/user-quotameter" )}

    ## load the frame manager
    <script type="text/javascript">

        ## load additional style sheet
        if (window != window.top)
            $('<link href="' + galaxy_config.root + 'static/style/galaxy.frame.masthead.css" rel="stylesheet">').appendTo('head');

        ## load galaxy js-modules
        require(['galaxy.master', 'galaxy.menu', 'galaxy.modal', 'galaxy.frame', 'galaxy.upload'],
        function(mod_master, mod_menu, mod_modal, mod_frame, mod_upload)
        {
            ## check if master is available
            if (Galaxy.master)
                return;

            ## get configuration
            var master_config = ${ h.to_json_string( master_config ) };

            ## set up the quota meter (And fetch the current user data from trans)
            Galaxy.currUser = new User(master_config.user.json);

            ## load global galaxy objects
            Galaxy.master = new mod_master.GalaxyMaster(master_config);
            Galaxy.modal = new mod_modal.GalaxyModal();
            Galaxy.frame_manager = new mod_frame.GalaxyFrameManager();

            ## construct default menu options
            Galaxy.menu = new mod_menu.GalaxyMenu({
                master: Galaxy.master,
                config: master_config
            });
            
            ## add upload plugin
            ##Galaxy.upload = new mod_upload.GalaxyUpload();

            ## add quota meter to master
            Galaxy.quotaMeter = new UserQuotaMeter({
                model   : Galaxy.currUser,
                el      : $(Galaxy.master.el).find('.quota-meter-container')
            }).render();
        });
    </script>
</%def>
