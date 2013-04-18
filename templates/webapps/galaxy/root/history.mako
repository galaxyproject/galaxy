<%inherit file="/base.mako"/>

<%def name="title()">
    ${_('Galaxy History')}
</%def>

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
            'View data',
            'Edit attributes',
            'Delete',
            'Job is waiting to run',
            'View Details',
            'Job is currently running',
            #'Run this job again',
            'Metadata is being Auto-Detected.',
            'No data: ',
            'format: ',
            'database: ',
            #TODO localized data.dbkey??
            'Info: ',
            #TODO localized display_app.display_name??
            # _( link_app.name )
            # localized peek...ugh
            'Error: unknown dataset state',
        ]
        return strings_to_localize
    %>
</%def>

## ---------------------------------------------------------------------------------------------------------------------
## all the possible history urls (primarily from web controllers at this point)
<%def name="get_history_url_templates()">
<%
    from urllib import unquote_plus

    history_class_name      = 'History'
    encoded_id_template     = '<%= id %>'

    url_dict = {
        'rename'        : h.url_for( controller="history", action="rename_async",
                            id=encoded_id_template ),
        'tag'           : h.url_for( controller='tag', action='get_tagging_elt_async',
                            item_class=history_class_name, item_id=encoded_id_template ),
        'annotate'      : h.url_for( controller="history", action="annotate_async",
                            id=encoded_id_template )
    }
%>
${ unquote_plus( h.to_json_string( url_dict ) ) }
</%def>

## ---------------------------------------------------------------------------------------------------------------------
## all the possible hda urls (primarily from web controllers at this point) - whether they should have them or not
##TODO: unify url_for btwn web, api
<%def name="get_hda_url_templates()">
<%
    from urllib import unquote_plus

    hda_class_name      = 'HistoryDatasetAssociation'
    encoded_id_template = '<%= id %>'

    hda_ext_template    = '<%= file_ext %>'
    meta_type_template  = '<%= file_type %>'

    url_dict = {
        # ................................................................ warning message links
        'purge' : h.url_for( controller='dataset', action='purge_async',
            dataset_id=encoded_id_template ),
        #TODO: hide (via api)
        'unhide' : h.url_for( controller='dataset', action='unhide',
            dataset_id=encoded_id_template ),
        #TODO: via api
        'undelete' : h.url_for( controller='dataset', action='undelete',
            dataset_id=encoded_id_template ),

        # ................................................................ title actions (display, edit, delete),
        'display' : h.url_for( controller='dataset', action='display',
            dataset_id=encoded_id_template, preview=True, filename='' ),
        'edit' : h.url_for( controller='dataset', action='edit',
            dataset_id=encoded_id_template ),

        #TODO: via api
        'delete' : h.url_for( controller='dataset', action='delete_async',
            dataset_id=encoded_id_template ),

        # ................................................................ download links (and associated meta files),
        'download' : h.url_for( controller='dataset', action='display',
            dataset_id=encoded_id_template, to_ext=hda_ext_template ),
        'meta_download' : h.url_for( controller='dataset', action='get_metadata_file',
            hda_id=encoded_id_template, metadata_name=meta_type_template ),

        # ................................................................ primary actions (errors, params, rerun),
        'report_error' : h.url_for( controller='dataset', action='errors',
            id=encoded_id_template ),
        'show_params' : h.url_for( controller='dataset', action='show_params',
            dataset_id=encoded_id_template ),
        'rerun' : h.url_for( controller='tool_runner', action='rerun',
            id=encoded_id_template ),
        'visualization' : h.url_for( controller='visualization', action='index' ),

        # ................................................................ secondary actions (tagging, annotation),
        'tags' : {
            'get' : h.url_for( controller='tag', action='get_tagging_elt_async',
                item_class=hda_class_name, item_id=encoded_id_template ),
            'set' : h.url_for( controller='tag', action='retag',
                item_class=hda_class_name, item_id=encoded_id_template ),
        },
        'annotation' : {
            'get' : h.url_for( controller='dataset', action='get_annotation_async',
                id=encoded_id_template ),
            'set' : h.url_for( controller='/dataset', action='annotate_async',
                id=encoded_id_template ),
        },
    }
%>
${ unquote_plus( h.to_json_string( url_dict ) ) }
</%def>


## -----------------------------------------------------------------------------
<%def name="get_current_user()">
<%
    #TODO: move to root.history, using base.controller.usesUser, unify that with users api
    user_json = trans.webapp.api_controllers[ 'users' ].show( trans, 'current' )
    return user_json
%>
</%def>


## -----------------------------------------------------------------------------
<%def name="javascripts()">
${parent.javascripts()}

${h.js(
    "libs/jquery/jstorage",
    "libs/jquery/jquery.autocomplete", "galaxy.autocom_tagging",
    "mvc/base-mvc",
)}

${h.templates(
    "helpers-common-templates",
    "template-warningmessagesmall",
    
    "template-history-historyPanel",

    "template-hda-warning-messages",
    "template-hda-titleLink",
    "template-hda-failedMetadata",
    "template-hda-hdaSummary",
    "template-hda-downloadLinks",
    "template-hda-tagArea",
    "template-hda-annotationArea",
    "template-hda-displayApps",
)}

##TODO: fix: curr hasta be _after_ h.templates bc these use those templates - move somehow
${h.js(
    "mvc/user/user-model", "mvc/user/user-quotameter",
    "mvc/dataset/hda-model", "mvc/dataset/hda-base", "mvc/dataset/hda-edit",
    "mvc/history/history-model", "mvc/history/history-panel"
)}
    
<script type="text/javascript">
function galaxyPageSetUp(){
    //TODO: move to base.mako
    // moving global functions, objects into Galaxy namespace
    top.Galaxy                  = top.Galaxy || {};
    
    if( top != window ){
        top.Galaxy.mainWindow       = top.Galaxy.mainWindow     || top.frames.galaxy_main;
        top.Galaxy.toolWindow       = top.Galaxy.toolWindow     || top.frames.galaxy_tools;
        top.Galaxy.historyWindow    = top.Galaxy.historyWindow  || top.frames.galaxy_history;

        //modals
        top.Galaxy.show_modal       = top.show_modal;
        top.Galaxy.hide_modal       = top.hide_modal;
    }

    top.Galaxy.localization     = GalaxyLocalization;
    window.Galaxy = top.Galaxy;
}

// set js localizable strings
GalaxyLocalization.setLocalizedString( ${ create_localization_json( get_page_localized_strings() ) } );

// add needed controller urls to GalaxyPaths
if( !galaxy_paths ){ galaxy_paths = top.galaxy_paths || new GalaxyPaths(); }
galaxy_paths.set( 'hda', ${get_hda_url_templates()} );
galaxy_paths.set( 'history', ${get_history_url_templates()} );

$(function(){
    galaxyPageSetUp();
    // ostensibly, this is the App

    //NOTE: for debugging on non-local instances (main/test)
    //  1. load history panel in own tab
    //  2. from console: new PersistantStorage( '__history_panel' ).set( 'debugging', true )
    //  -> history panel and hdas will display console logs in console
    var debugging = false;
    if( jQuery.jStorage.get( '__history_panel' ) ){
        debugging = new PersistantStorage( '__history_panel' ).get( 'debugging' );
    }

    // get the current user (either from the top frame's Galaxy or if in tab via the bootstrap)
    Galaxy.currUser = Galaxy.currUser || new User(${ get_current_user() });
    if( debugging ){ Galaxy.currUser.logger = console; }

    var page_show_deleted = ${ 'true' if show_deleted == True else ( 'null' if show_deleted == None else 'false' ) },
        page_show_hidden  = ${ 'true' if show_hidden  == True else ( 'null' if show_hidden  == None else 'false' ) },

    //  ...use mako to 'bootstrap' the models
        historyJson = ${ history_json },
        hdaJson     = ${ hda_json };

    //TODO: add these two in root.history
    // add user data to history
    // i don't like this history+user relationship, but user authentication changes views/behaviour
    historyJson.user = Galaxy.currUser.toJSON();

    // set up messages passed in
    %if message:
    historyJson.message = "${_( message )}"; historyJson.status = "${status}";
    %endif

    // create the history panel
    var history = new History( historyJson, hdaJson, ( debugging )?( console ):( null ) );
    var historyPanel = new HistoryPanel({
            model           : history,
            urlTemplates    : galaxy_paths.attributes,
            logger          : ( debugging )?( console ):( null ),
            // is page sending in show settings? if so override history's
            show_deleted    : page_show_deleted,
            show_hidden     : page_show_hidden
        });
    historyPanel.render();

    // set up messages passed in
    %if hda_id:
    var hdaId = "${hda_id}";
    // have to fake 'once' here - simplify when bbone >= 1.0
    historyPanel.on( 'rendered:initial', function scrollOnce(){
        this.off( 'rendered:initial', scrollOnce, this );
        this.scrollToId( hdaId );
    }, historyPanel );
    %endif

    // QUOTA METER is a cross-frame ui element (meter in masthead, watches hist. size built here)
    //TODO: the quota message (curr. in the history panel) belongs somewhere else
    //TODO: does not display if in own tab
    if( Galaxy.quotaMeter ){
        // unbind prev. so we don't build up massive no.s of event handlers as history refreshes
        if( top.Galaxy.currHistoryPanel ){
            Galaxy.quotaMeter.unbind( 'quota:over',  top.Galaxy.currHistoryPanel.showQuotaMessage );
            Galaxy.quotaMeter.unbind( 'quota:under', top.Galaxy.currHistoryPanel.hideQuotaMessage );
        }

        // show/hide the 'over quota message' in the history when the meter tells it to
        Galaxy.quotaMeter.bind( 'quota:over',  historyPanel.showQuotaMessage, historyPanel );
        Galaxy.quotaMeter.bind( 'quota:under', historyPanel.hideQuotaMessage, historyPanel );

        // update the quota meter when current history changes size
        //TODO: can we consolidate the two following?
        historyPanel.model.bind( 'rendered:initial change:nice_size', function(){
            if( Galaxy.quotaMeter ){ Galaxy.quotaMeter.update() }
        });

        // having to add this to handle re-render of hview while overquota (the above do not fire)
        historyPanel.on( 'rendered rendered:initial', function(){
            if( Galaxy.quotaMeter && Galaxy.quotaMeter.isOverQuota() ){
                historyPanel.showQuotaMessage();
            }
        });
    }
    // set it up to be accessible across iframes
    top.Galaxy.currHistoryPanel = historyPanel;

    //ANOTHER cross-frame element is the history-options-button...
    //TODO: the options-menu stuff need to be moved out when iframes are removed
    //TODO: move to pub-sub
    //TODO: same strings ("Include...") here as in index.mako - brittle
    if( ( top.document !== window.document ) &&  ( Galaxy.historyOptionsMenu ) ){
        Galaxy.historyOptionsMenu.findItemByHtml( "${"Include Deleted Datasets"}" ).checked =
            Galaxy.currHistoryPanel.storage.get( 'show_deleted' );
        Galaxy.historyOptionsMenu.findItemByHtml( "${"Include Hidden Datasets"}" ).checked =
            Galaxy.currHistoryPanel.storage.get( 'show_hidden' );
    }

    return;
});
</script>
    
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css(
        "base",
        "history",
        "autocomplete_tagging"
    )}
    <style>
        ## TODO: move to base.less
        /*---- page level */
        .warningmessagesmall {
            margin: 8px 0 0 0;
        }
        #message-container div {
        }
        #message-container [class$="message"] {
            margin: 8px 0 0 0;
            cursor: pointer;
        }

        /*---- history level */
        #history-controls {
            margin-bottom: 5px;
            padding: 5px;
        }

        #history-title-area {
            margin: 0px 0px 5px 0px;
        }
        #history-name {
            word-wrap: break-word;
            font-weight: bold;
            /*color: gray;*/
        }
        .editable-text {
            border: solid transparent 1px;
        }
        #history-name-container input {
            width: 90%;
            margin: -2px 0px -3px -4px;
            font-weight: bold;
        }

        #quota-message-container {
            margin: 8px 0px 5px 0px;
        }
        #quota-message {
            margin: 0px;
        }

        #history-subtitle-area {
        }
        #history-size {
        }
        #history-secondary-links {
        }

        #history-secondary-links #history-refresh {
            text-decoration: none;
        }
        /*too tweaky*/
        #history-annotate {
            margin-right: 3px;
        }

        #history-tag-area, #history-annotation-area {
            margin: 10px 0px 10px 0px;
        }

        /*---- HDA level */
        .historyItem div.errormessagesmall {
            font-size: small;
            margin: 0px 0px 4px 0px;
        }
        .historyItem div.warningmessagesmall {
            font-size: small;
            margin: 0px 0px 4px 0px;
        }
        .historyItemBody {
            display: none;
        }

        .historyItemTitle {
            text-decoration: underline;
            cursor: pointer;
        }
        .historyItemTitle:hover {
            text-decoration: underline;
        }

    </style>
</%def>

<body class="historyPage"></body>
