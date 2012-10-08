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
    #print '\n', hda.name

    data_dict = {}
    def add_to_data( **kwargs ):
        data_dict.update( kwargs )
    
    #TODO??: better way to do urls (move into js galaxy_paths (decorate) - _not_ dataset specific)
    deleted = hda.deleted
    purged  = hda.purged
    
    # ................................................................ link actions 
    #purged  = purged or hda.dataset.purged //??
    # all of these urls are 'datasets/data_id/<action>
    if not ( dataset_purged or purged ) and for_editing:
        add_to_data( undelete_url=h.url_for( controller='dataset', action='undelete', dataset_id=encoded_data_id ) )
        # trans
        if trans.app.config.allow_user_dataset_purge:
            add_to_data( purge_url=h.url_for( controller='dataset', action='purge', dataset_id=encoded_data_id ) )
        
    if not hda.visible:
        add_to_data( unhide_url=h.url_for( controller='dataset', action='unhide', dataset_id=encoded_data_id ) )
    
    
    # ................................................................ title actions (display, edit, delete)
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
            edit_url = h.url_for( controller='dataset', action='edit',
                                  dataset_id=encoded_data_id )
            add_to_data( edit_url=edit_url )
    
    # delete button
    if for_editing and not ( deleted or dataset_purged or purged ):
        delete_url = h.url_for( controller='dataset', action='delete',
                                dataset_id=encoded_data_id,
                                show_deleted_on_refresh=show_deleted )
        add_to_data( delete_url=delete_url )
            
    # ................................................................ primary actions (error, info, download)
    # download links (hda and associated meta files)
    if not hda.purged:
        add_to_data( download_url=h.url_for( controller='/dataset', action='display',
                                             dataset_id=encoded_data_id, to_ext=hda.ext ) )
    
        meta_files = []
        for k in hda.metadata.spec.keys():
            if isinstance( hda.metadata.spec[ k ].param, FileParameter ):
                file_type = k
                download_url = h.url_for( controller='/dataset', action='get_metadata_file', 
                                          hda_id=encoded_data_id, metadata_name=file_type )
                meta_files.append( dict( meta_file_type=file_type, meta_download_url=download_url ) )
                
        if meta_files:
            add_to_data( meta_files=meta_files )
                
    # error report
    if for_editing:
        #NOTE: no state == 'error' check
        ##TODO: has to have an _UN_ encoded id
        #report_error_url = h.url_for( controller='dataset', action='errors', id=encoded_data_id )
        report_error_url = h.url_for( controller='dataset', action='errors', id=hda.id )
        add_to_data( report_error_url=report_error_url )
    
    # info/params
    show_params_url = h.url_for( controller='dataset', action='show_params', dataset_id=encoded_data_id )
    add_to_data( show_params_url=show_params_url )
    
    # rerun
    if for_editing:
        ##TODO: has to have an _UN_ encoded id
        #rerun_url = h.url_for( controller='tool_runner', action='rerun', id=encoded_data_id )
        rerun_url = h.url_for( controller='tool_runner', action='rerun', id=hda.id )
        add_to_data( rerun_url=rerun_url )
    
    # visualizations
    if hda.ext in app.datatypes_registry.get_available_tracks():
        # do these need _localized_ dbkeys?
        trackster_urls = {}
        if hda.dbkey != '?':
            data_url = h.url_for( controller='visualization', action='list_tracks', dbkey=hda.dbkey )
            data_url = hda.replace( 'dbkey', 'f-dbkey' )
        else:
            data_url = h.url_for( controller='visualization', action='list_tracks' )
        trackster_urls[ 'hda-url' ]   = data_url
        trackster_urls[ 'action-url' ] = h.url_for( controller='visualization', action='trackster', dataset_id=encoded_data_id )
        trackster_urls[ 'new-url' ]    = h.url_for( controller='visualization', action='trackster', dataset_id=encoded_data_id, default_dbkey=hda.dbkey )
        add_to_data( trackster_url=trackster_urls )
    
    # display apps (igv, uscs)
    display_types = []
    display_apps = []
    if( hda.state in [ 'ok', 'failed_metadata' ]
    and hda.has_data() ):
        #NOTE: these two data share structures
        #TODO: this doesn't seem to get called with the hda I'm using. What would call this? How can I spoof it?
        for display_type in hda.datatype.get_display_types():
            display_label = hda.datatype.get_display_label( display_type )
            target_frame, display_links = hda.datatype.get_display_links( hda, display_type, app, request.base )
            if display_links:
                display_links = []
                for display_name, display_href in display_links:
                    display_type_link = dict(
                        target  = target_frame,
                        href    = display_href,
                        text    = display_name
                    )
                    display_links.append( display_type_link )
                
                # append the link list to the main map using the display_label
                display_types.append( dict( label=display_label, links=display_links ) )

        for display_app in hda.get_display_applications( trans ).itervalues():
            app_links = []
            for display_app_link in display_app.links.itervalues():
                app_link = dict(
                    target = display_app_link.url.get( 'target_frame', '_blank' ),
                    href = display_app_link.get_display_url( hda, trans ),
                    text = _( display_app_link.name )
                )
                app_links.append( app_link )
            
            display_apps.append( dict( label=display_app.name, links=app_links ) )
                
    # attach the display types and apps (if any) to the hda obj
    #if display_types: print 'display_types:', display_types
    #if display_apps: print 'display_apps:', display_apps
    add_to_data( display_types=display_types )
    add_to_data( display_apps=display_apps )

    # ................................................................ secondary actions (tagging, annotation)
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

##TODO: remove after filling tags.js
<%namespace file="../tagging_common.mako" import="render_individual_tagging_element" />
<%def name="context_to_js()">
<%
    ##print 'context', context, dir( context )
    ##print 'context.kwargs', context.kwargs
    ##print 'history:', history
    
    ##TODO: move to API
    
    for_editing = True
    context_dict = {
        'history'       : { 
            'id'            : trans.security.encode_id( history.id ),
            'name'          : history.name,
            
            'status'        : status,
            'showDeleted' 	: show_deleted,
            'showHidden' 	: show_hidden,
            'quotaMsg' 		: over_quota,
            'message' 		: message, ##'go outside'
            
            'deleted'       : history.deleted,
            'diskSize'      : history.get_disk_size( nice_size=True ),
        
            ## maybe security issues...
            'userIsAdmin'   : trans.user_is_admin(),
            'userRoles'     : [ role.get_api_value() for role in trans.get_current_user_roles() ],
            
            ##tagging_common.mako: render_individual_tagging_element(user=trans.get_user(),
            ##    tagged_item=history, elt_context="history.mako", use_toggle_link=False, input_size="20")
            'tags'          : [],
            ##TODO: broken - of course
            ##TODO: remove after filling tags.js
            ##'tagHTML'       : render_individual_tagging_element(
            ##                    user=trans.get_user(),
            ##                    tagged_item=history,
            ##                    elt_context="history.mako",
            ##                    use_toggle_link=False,
            ##                    input_size="20"),
            ##TODO:?? h.to_unicode( annotation ) | h
            'annotation'    : h.to_unicode( annotation ),

            ##TODO: broken
            'baseURL'           : h.url_for( 'history', show_deleted=show_deleted ),
            'hideDeletedURL'    : h.url_for( 'history', show_deleted=False ),
            'hideHiddenURL'     : h.url_for( 'history', show_hidden=False ),
            'tagURL'            : h.url_for( controller='history', action='tag' ),
            'annotateURL'       : h.url_for( controller='history', action='annotate' )
        },
        'hdas'          : [ prep_hda( hda, for_editing ) for hda in datasets ],
        
        # some of these may be unneeded when all is said and done...
        'hdaId' 		: hda_id,
        'forEditing'    : for_editing,
    }
%>
${ h.to_json_string( context_dict ) }
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    
    ${h.js(
        "libs/jquery/jstorage",
        "libs/jquery/jquery.autocomplete", "galaxy.autocom_tagging",
        "libs/json2",
        "mvc/base-mvc", "mvc/ui"
    )}

    ${h.templates(
        "helpers-common-templates",
        "template-warningmessagesmall",
        
        "template-history-warning-messages",
        "template-history-titleLink",
        "template-history-failedMetadata",
        "template-history-hdaSummary",
        "template-history-downloadLinks",
        "template-history-tagArea",
        "template-history-annotationArea",
        "template-history-displayApps",
        
        "template-history-historyPanel"
    )}
    
    ##TODO: fix: curr hasta be _after_ h.templates - move somehow
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
        if( console && console.debug ){
            window.pageData = pageData;
            
            ##_.each( pageData.hdas, function( hda ){
            ##    console.debug( hda );
            ##});
        }
        
        // on ready
        USE_CURR_DATA = true;
        $(function(){
            if( console && console.debug ){ console.debug( 'using backbone.js in history panel' ); }
            
            if ( window.USE_CURR_DATA ){
                // Navigate to a dataset.
                if( pageData.hdaId ){
                    self.location = "#" + pageData.hdaId;
                }
                var glx_history = new History( pageData.history ).loadDatasetsAsHistoryItems( pageData.hdas ),
                    glx_history_view = new HistoryView({ model: glx_history });
                glx_history_view.render();
                window.glx_history = glx_history; window.glx_history_view = glx_history_view;
                
                return;
            
            } else {
                // sandbox
            }
        });
    </script>
    
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css("base", "history", "autocomplete_tagging" )}
	<style>
        ## TODO: move to base.less
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
