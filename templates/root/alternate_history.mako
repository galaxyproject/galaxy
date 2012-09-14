<%inherit file="/base.mako"/>

## ---------------------------------------------------------------------------------------------------------------------
<%def name="create_localization_json( strings_to_localize )">
    ## converts strings_to_localize (a list of strings) into a JSON dictionary of { string : localized string }
${ h.to_json_string( dict([ ( string, _(string) ) for string in strings_to_localize ]) ) }
## ?? add: if string != _(string)
</%def>

<%def name="get_page_localized_strings()">
    ## a list of localized strings used in the backbone views, etc. (to be loaded and cached)
    ##! change on per page basis
    <%
        strings_to_localize = [
            
            # from history.mako
            # not needed?: "Galaxy History",
            'refresh',
            'collapse all',
            'hide deleted',
            'hide hidden',
            'You are currently viewing a deleted history!',
            "Your history is empty. Click 'Get Data' on the left pane to start",
            
            # from history_common.mako
            'Download',
            'Display Data',
            'Display data in browser',
            'Edit attributes',
            'Delete',
            'Job is waiting to run',
            'View Details',
            'Run this job again',
            'Job is currently running',
            'View Details',
            'Run this job again',
            'Metadata is being Auto-Detected.',
            'No data: ',
            'format: ',
            'database: ',
            # localized data.dbkey?? - localize in the datasetup above
            'Info: ',
            # localized display_app.display_name?? - localize above
            # _( link_app.name )
            # localized peek...ugh
            'Error: unknown dataset state',
        ]
        return strings_to_localize
    %>
</%def>


## ---------------------------------------------------------------------------------------------------------------------
<%def name="get_urls_for_hda( hda, encoded_data_id, for_editing )">
<%
    from galaxy.datatypes.metadata import FileParameter

    data_dict = {}
    def add_to_data( **kwargs ):
        data_dict.update( kwargs )
    
    # download links (for both main hda and associated meta files)
    if hda.has_data():
        add_to_data( download_url=h.url_for( controller='/dataset', action='display',
                                             dataset_id=encoded_data_id, to_ext=hda.ext ) )
    
        download_meta_urls = {}
        for file_type in hda.metadata.spec.keys():
            if not isinstance( hda.metadata.spec[ file_type ].param, FileParameter ):
                continue
                
            download_meta_urls[ file_type ] = h.url_for( controller='/dataset', action='get_metadata_file', 
                                                         hda_id=encoded_data_id, metadata_name=file_type )
        if download_meta_urls:
            #TODO:?? needed? isn't this the same as download_url?
            add_to_data( download_dataset_url=h.url_for( controller='dataset', action='display',
                                                         dataset_id=encoded_data_id, to_ext=hda.ext ) )
            add_to_data( download_meta_urls=download_meta_urls )
        
    #TODO??: better way to do urls (move into js galaxy_paths (decorate) - _not_ dataset specific)
    deleted = hda.deleted
    purged  = hda.purged
    
    #purged  = purged or hda.dataset.purged //??
    
    # all of these urls are 'datasets/data_id/<action>
    if not ( dataset_purged or purged ) and for_editing:
        add_to_data( undelete_url=h.url_for( controller='dataset', action='undelete', dataset_id=encoded_data_id ) )
        # trans
        if trans.app.config.allow_user_dataset_purge:
            add_to_data( purge_url=h.url_for( controller='dataset', action='purge', dataset_id=encoded_data_id ) )
        
    if not hda.visible:
        add_to_data( unhide_url=h.url_for( controller='dataset', action='unhide', dataset_id=encoded_data_id ) )
    
    display_url = ''
    if for_editing:
        display_url = h.url_for( controller='dataset', action='display', dataset_id=encoded_data_id, preview=True, filename='' )
    else:
        # Get URL for display only.
        if hda.history.user and hda.history.user.username:
            display_url = h.url_for( controller='dataset', action='display_by_username_and_slug',
                                     username=hda.history.user.username, slug=encoded_data_id, filename='' )
        else:
            # HACK: revert to for_editing display URL when there is no user/username. This should only happen when
            # there's no user/username because dataset is being displayed by history/view after error reported.
            # There are no security concerns here because both dataset/display and dataset/display_by_username_and_slug
            # check user permissions (to the same degree) before displaying.
            display_url = h.url_for( controller='dataset', action='display', dataset_id=encoded_data_id, preview=True, filename='' )
    add_to_data( display_url=display_url )
    
    # edit attr button
    if for_editing:
        if not( hda.deleted or hda.purged ):
            edit_url = h.url_for( controller='dataset', action='edit', dataset_id=encoded_data_id )
            add_to_data( edit_url=edit_url )
    
    # delete button
    if for_editing and not ( deleted or dataset_purged or purged ):
        add_to_data( delete_url=h.url_for( controller='dataset', action='delete', dataset_id=encoded_data_id,
                                           ##TODO: loose end
                                           show_deleted_on_refresh=show_deleted
        ))
            
    # error report
    if for_editing:
        #NOTE: no state == 'error' check
        add_to_data( report_error_url=h.url_for( h.url_for( controller='dataset', action='errors', id=encoded_data_id ) ) )
            
    if hda.ext in app.datatypes_registry.get_available_tracks():
        # do these need _localized_ dbkeys?
        trackster_urls = {}
        if hda.dbkey != '?':
            data_url = h.url_for( controller='visualization', action='list_tracks', dbkey=hda.dbkey )
            data_url = hda.replace( 'dbkey', 'f-dbkey' )
        else:
            data_url = h.url_for( controller='visualization', action='list_tracks' )
        trackster_urls[ 'hda-url' ]   = data_url
        trackster_urls[ 'action-url' ] = h.url_for( controller='tracks', action='browser', dataset_id=encoded_data_id )
        trackster_urls[ 'new-url' ]    = h.url_for( controller='tracks', action='index',   dataset_id=encoded_data_id, default_dbkey=hda.dbkey )
        add_to_data( trackster_url=trackster_urls )
    
    if trans.user:
        add_to_data( ajax_get_tag_url=( h.url_for(
            controller='tag', action='get_tagging_elt_async',
            item_class=hda.__class__.__name__, item_id=encoded_data_id ) ) )
        add_to_data( retag_url=( h.url_for(
            controller='tag', action='retag',
            item_class=hda.__class__.__name__, item_id=encoded_data_id ) ) )
            
        add_to_data( annotate_url=( h.url_for( controller='dataset', action='annotate', id=encoded_data_id ) ) )
        add_to_data( ajax_get_annotation_url=( h.url_for(
            controller='dataset', action='get_annotation_async', id=encoded_data_id ) ) )
        add_to_data( ajax_set_annotation_url=( h.url_for(
            controller='/dataset', action='annotate_async', id=encoded_data_id ) ) )
                    
    display_type_display_links = {}
    #TODO: this doesn't seem to get called with the hda I'm using. What would call this? How can I spoof it?
    for display_app in hda.datatype.get_display_types():
        # print "display_app:", display_app
        target_frame, display_links = hda.datatype.get_display_links( hda, display_app, app, request.base )
        # print "target_frame:", target_frame, "display_links:", display_links
        #if len( display_links ) > 0:
        #    display_type_display_links[ display_app ] = {}
        #    for display_name, display_link in display_links:
        #NOTE!: localized name
            #<a target="${target_frame}" href="${display_link}">${_(display_name)}</a>
            #pass
        # <br />
    
    display_apps = {}
    for display_app in hda.get_display_applications( trans ).itervalues():
        display_app_dict = display_apps[ display_app.name ] = {}
        for link_app in display_app.links.itervalues():
            # print link_app.name, link_app.get_display_url( hda, trans )
            #NOTE!: localized name
            display_app_dict[ _( link_app.name ) ] = {
                'url' : link_app.get_display_url( hda, trans ),
                'target' : link_app.url.get( 'target_frame', '_blank' )
            }
    if display_apps:
        # print display_apps
        add_to_data( display_apps=display_apps )

    return data_dict
%>
</%def>

<%def name="prep_hda( data, for_editing )">
<%
    from pprint import pformat
    ## 'datasets' passed from root.history are HistoryDatasetAssociations
    ##      these datas _have_ a Dataset (data.dataset) 
    #ported mostly from history_common
    #post: return dictionary form 
    #??: move out of templates?
    #??: gather data from model?
    
    DATASET_STATE = trans.app.model.Dataset.states
    # {'OK': 'ok', 'FAILED_METADATA': 'failed_metadata', 'UPLOAD': 'upload',
    # 'DISCARDED': 'discarded', 'RUNNING': 'running', 'SETTING_METADATA': 'setting_metadata',
    # 'ERROR': 'error', 'NEW': 'new', 'QUEUED': 'queued', 'EMPTY': 'empty'}
    #TODO: move to Dataset.states? how often are these used?
    STATES_INTERPRETED_AS_QUEUED = [ 'no state', '', None ]
    
    #TODO: clean up magic strings
    #TODO: format to 120
    data_dict = data.get_api_value()
    
    # convert/re-format api values as needed
    #TODO: use data_dict.update to add these (instead of localvars)
    def add_to_data( **kwargs ):
        data_dict.update( kwargs )
    
    # trans
    add_to_data( hid=data.hid )
    encoded_data_id = trans.security.encode_id( data.id )
    add_to_data( id=encoded_data_id )

    # localize dbkey
    data_dict[ 'metadata_dbkey' ] = _( data_dict[ 'metadata_dbkey' ] )

    add_to_data( state=data.state )
    if data_state in STATES_INTERPRETED_AS_QUEUED:
        #TODO: magic string
        add_to_data( state=DATASET_STATE.QUEUED )
    
    # trans
    current_user_roles = trans.get_current_user_roles()
    add_to_data( can_edit=( not ( data.deleted or data.purged ) ) )
    
    # considered accessible if user can access or user isn't admin
    # trans
    accessible = trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset )
    accessible = trans.user_is_admin() or accessible
    add_to_data( accessible=accessible )

    url_dict = get_urls_for_hda( data, encoded_data_id, for_editing )
    data_dict.update( url_dict )
    #print 'url_dict:', pformat( url_dict, indent=2 )
    #print 'data_dict:', pformat( data_dict, indent=2 ), "\n"
    #print data_dict

    if data.peek != "no peek":
        add_to_data( peek=( _( h.to_unicode( data.display_peek() ) ) ) )

    return data_dict
%>
</%def>


<%def name="context_to_js()">
<%
    ##print 'context', context, dir( context )
    ##print 'context.kwargs', context.kwargs
    ##print 'history:', history
    
    user_is_admin = trans.user_is_admin()
    user_roles = trans.get_current_user_roles()
    prepped_hdas = [
        prep_hda( hda, True ) for hda in datasets ]
    
    context_dict = {
        'history'       : { 
            'id'    : trans.security.encode_id( history.id ),
            'name'  : history.name
        },
        'annotation'    : annotation,
        'hdas'          : prepped_hdas,
        'hdaId' 		: hda_id,
        'showDeleted' 	: show_deleted,
        'showHidden' 	: show_hidden,
        'quotaMsg' 		: over_quota,
        'message' 		: message,
        'status' 		: status,
        
        # some of these may be unneeded when all is said and done...
        'forEditing'    : True,
        
        ## maybe security issues...
        'userIsAdmin'   : user_is_admin,
        'userRoles'     : [ role.get_api_value() for role in user_roles ],
        
    }
%>
${ h.to_json_string( context_dict ) }
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    
    ${h.js(
        "libs/jquery/jstorage", "libs/jquery/jquery.autocomplete",
        ##"libs/handlebars.full",
        "galaxy.autocom_tagging",
        "mvc/base-mvc", "mvc/ui"
    )}

    ${h.templates(
        "helpers-common-templates",
        "template-warningmessagesmall",
        
        "template-history-warning-messages",
        "template-history-titleLink",
        "template-history-hdaSummary",
        "template-history-failedMetadata",
        "template-history-tagArea",
        "template-history-annotationArea"
    )}
    
    ## if using in-dom templates they need to go here (before the Backbone classes are defined)
    ##NOTE: it's impossible(?) to include _ templates in this way bc they use identical delims as mako
    ##  (without altering Underscore.templateSettings)
    ##<%include file="../../static/scripts/templates/common-templates.html" />
    ##<%include file="../../static/scripts/templates/history-templates.html" />
    
    ${h.js(
        "mvc/history"
        ##"mvc/tags", "mvc/annotations"
    )}
    
    <script type="text/javascript">
        GalaxyLocalization.setLocalizedString( ${ create_localization_json( get_page_localized_strings() ) } );
        // add needed controller urls to GalaxyPaths
        galaxy_paths.set( 'dataset_path', "${h.url_for( controller='dataset' )}" )
        
        // Init. on document load.
        var pageData = ${context_to_js()};
        
        //USE_MOCK_DATA = true;
        USE_CURR_DATA = true;
        
        // on ready
        $(function(){
            if( console && console.debug ){ console.debug( 'using backbone.js in history panel' ); }
            
            if( window.USE_MOCK_DATA ){
                if( console && console.debug ){ console.debug( '\t using mock data' ); }
                createMockHistoryData();
                return;
            
            } else if ( window.USE_CURR_DATA ){
                if( console && console.debug ){ console.debug( '\t using current history data' ); }
                glx_history = new History( pageData.history ).loadDatasetsAsHistoryItems( pageData.hdas );
                glx_history_view = new HistoryView({ model: glx_history });
                glx_history_view.render();
                
                hi = glx_history.items.at( 0 );
                hi_view = new HistoryItemView({ model: hi });
                $( 'body' ).append( hi_view.render() );
                return;
            }
            
            // sandbox here
            // testing iconButton
            //ibm = new IconButton({
            //    icon_class : 'information',
            //    on_click : function( event ){ console.debug( 'blerg' ); },
            //});
            //mockObj = { one : 1 };
            //ibv = new IconButtonView({ model : ibm });
            //new_click = function( event ){ console.debug( mockObj.one ); }
            //$( 'body' ).append( ibv.render().$el );
            
        });
    </script>
    
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css("base", "history", "autocomplete_tagging" )}
	<style>"
		.historyItemBody {
			display: none;
		}
		div.form-row {
			padding: 5px 5px 5px 0px;
		}
		#top-links {
			margin-bottom: 15px;
		}
		#history-name-container {
			color: gray;
			font-weight: bold;
		}
		#history-name {
			word-wrap: break-word;
		}
		.editable-text {
			border: solid transparent 1px;
			padding: 3px;
			margin: -4px;
		}
	</style>
	
	<noscript>
		## js disabled: degrade gracefully
		<style>
		.historyItemBody {
			display: block;
		}
		</style>
	</noscript>
</%def>

<%def name="title()">
	${_('Galaxy History')}
</%def>

<body class="historyPage"></body>
