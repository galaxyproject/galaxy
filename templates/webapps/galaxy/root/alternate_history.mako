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
        ## havent been localized
        ##[
        ##    "anonymous user",
        ##    "Click to rename history",
        ##    "Click to see more actions",
        ##    "Edit history tags",
        ##    "Edit history annotation",
        ##    "Tags",
        ##    "Annotation",
        ##    "Click to edit annotation",
        ##    "You are over your disk ...w your allocated quota.",
        ##    "Show deleted",
        ##    "Show hidden",
        ##    "Display data in browser",
        ##    "Edit Attributes",
        ##    "Download",
        ##    "View details",
        ##    "Run this job again",
        ##    "Visualize",
        ##    "Edit dataset tags",
        ##    "Edit dataset annotation",
        ##    "Trackster",
        ##    "Circster",
        ##    "Scatterplot",
        ##    "GeneTrack",
        ##    "Local",
        ##    "Web",
        ##    "Current",
        ##    "main",
        ##    "Using"
        ##]
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

    history_class_name      = history.__class__.__name__
    encoded_id_template     = '<%= id %>'

    url_dict = {
        ##TODO: into their own MVs
        'rename'        : h.url_for( controller="/history", action="rename_async",
                            id=encoded_id_template ),
        'tag'           : h.url_for( controller='tag', action='get_tagging_elt_async',
                            item_class=history_class_name, item_id=encoded_id_template ),
        'annotate'      : h.url_for( controller="/history", action="annotate_async",
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
    #username_template   = '<%= username %>'
    hda_ext_template    = '<%= file_ext %>'
    meta_type_template  = '<%= file_type %>'

    display_app_name_template = '<%= name %>'
    display_app_link_template = '<%= link %>'

    url_dict = {
        # ................................................................ warning message links
        #'purge' : h.url_for( controller='dataset', action='purge',
        #    dataset_id=encoded_id_template ),
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
        #TODO:
        #'user_display_url' : h.url_for( controller='dataset', action='display_by_username_and_slug',
        #    username=username_template, slug=encoded_id_template, filename='' ),
        'edit' : h.url_for( controller='dataset', action='edit',
            dataset_id=encoded_id_template ),

        #TODO: via api
        'delete' : h.url_for( controller='dataset', action='delete_async', dataset_id=encoded_id_template ),

        # ................................................................ download links (and associated meta files),
        'download' : h.url_for( controller='/dataset', action='display',
            dataset_id=encoded_id_template, to_ext=hda_ext_template ),
        'meta_download' : h.url_for( controller='/dataset', action='get_metadata_file',
            hda_id=encoded_id_template, metadata_name=meta_type_template ),

        # ................................................................ primary actions (errors, params, rerun),
        'report_error' : h.url_for( controller='dataset', action='errors',
            id=encoded_id_template ),
        'show_params' : h.url_for( controller='dataset', action='show_params',
            dataset_id=encoded_id_template ),
        'rerun' : h.url_for( controller='tool_runner', action='rerun',
            id=encoded_id_template ),
        'visualization' : h.url_for( controller='visualization' ),

        # ................................................................ secondary actions (tagging, annotation),
        'tags' : {
            'get' : h.url_for( controller='tag', action='get_tagging_elt_async',
                item_class=hda_class_name, item_id=encoded_id_template ),
            'set' : h.url_for( controller='tag', action='retag',
                item_class=hda_class_name, item_id=encoded_id_template ),
        },
        'annotation' : {
            #TODO: needed? doesn't look like this is used (unless graceful degradation)
            #'annotate_url' : h.url_for( controller='dataset', action='annotate',
            #    id=encoded_id_template ),
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
## get the history, hda, user data from the api (as opposed to the web controllers/mako)

## I'd rather do without these (esp. the get_hdas which hits the db twice)
##   but we'd need a common map producer (something like get_api_value but more complete)
##TODO: api/web controllers should use common code, and this section should call that code
<%def name="get_history( id )">
<%
    history_json = trans.webapp.api_controllers[ 'histories' ].show( trans, trans.security.encode_id( id ) )
    #assert isinstance( history, dict ), (
    #    'Bootstrapped history was expecting a dictionary: %s' %( str( history ) ) )
    return history_json
%>
</%def>

<%def name="get_current_user()">
<%
    user_json = trans.webapp.api_controllers[ 'users' ].show( trans, 'current' )
    #assert isinstance( hdaDataList, list ), (
    #    'Bootstrapped current user was expecting a dictionary: %s' %( str( user ) ) )
    return user_json
%>
</%def>

<%def name="get_hdas( history_id, hdas )">
<%
    #BUG: one inaccessible dataset will error entire list
    if not hdas:
        return '[]'
    # rather just use the history.id (wo the datasets), but...
    hda_json = trans.webapp.api_controllers[ 'history_contents' ].index(
        trans, trans.security.encode_id( history_id ),
        ids=( ','.join([ trans.security.encode_id( hda.id ) for hda in hdas ]) ) )
    return hda_json
%>
</%def>


## -----------------------------------------------------------------------------
<%def name="javascripts()">
${parent.javascripts()}

${h.js(
    "libs/jquery/jstorage",
    "libs/jquery/jquery.autocomplete", "galaxy.autocom_tagging",
    ##"libs/json2",
    ##"libs/bootstrap",
    ## I think we can remove some of these
    ##"libs/backbone/backbone-relational",
    "mvc/base-mvc",
    ##"mvc/ui"
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
    
    "template-user-quotaMeter-quota",
    "template-user-quotaMeter-usage"
)}

##TODO: fix: curr hasta be _after_ h.templates bc these use those templates - move somehow
${h.js(
    "mvc/user/user-model", "mvc/user/user-quotameter",

    "mvc/dataset/hda-model",
    "mvc/dataset/hda-base",
    "mvc/dataset/hda-edit",

    ##"mvc/tags", "mvc/annotations"

    "mvc/history/history-model", "mvc/history/history-panel"
)}
    
<script type="text/javascript">
function galaxyPageSetUp(){
    // moving global functions, objects into Galaxy namespace
    top.Galaxy                  = top.Galaxy || {};
    
    // bad idea from memleak standpoint?
    top.Galaxy.mainWindow       = top.Galaxy.mainWindow     || top.frames.galaxy_main;
    top.Galaxy.toolWindow       = top.Galaxy.toolWindow     || top.frames.galaxy_tools;
    top.Galaxy.historyWindow    = top.Galaxy.historyWindow  || top.frames.galaxy_history;
    
    top.Galaxy.$masthead        = top.Galaxy.$masthead      || $( top.document ).find( 'div#masthead' );
    top.Galaxy.$messagebox      = top.Galaxy.$messagebox    || $( top.document ).find( 'div#messagebox' );
    top.Galaxy.$leftPanel       = top.Galaxy.$leftPanel     || $( top.document ).find( 'div#left' );
    top.Galaxy.$centerPanel     = top.Galaxy.$centerPanel   || $( top.document ).find( 'div#center' );
    top.Galaxy.$rightPanel      = top.Galaxy.$rightPanel    || $( top.document ).find( 'div#right' );

    //modals
    // other base functions

    // global backbone models
    top.Galaxy.currUser         = top.Galaxy.currUser;
    top.Galaxy.currHistoryPanel = top.Galaxy.currHistoryPanel;

    //top.Galaxy.paths            = galaxy_paths;

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

    //NOTE: for debugging on non-local instances (main/test)
    //  1. load history panel in own tab
    //  2. from console: new PersistantStorage( '__history_panel' ).set( 'debugging', true )
    //  -> history panel and hdas will display console logs in console
    var debugging = false;
    if( jQuery.jStorage.get( '__history_panel' ) ){
        debugging = new PersistantStorage( '__history_panel' ).get( 'debugging' );
    }

    // ostensibly, this is the App
    // LOAD INITIAL DATA IN THIS PAGE - since we're already sending it...
    //  ...use mako to 'bootstrap' the models
    var page_show_deleted = ${ 'true' if show_deleted == True else ( 'null' if show_deleted == None else 'false' ) },
        page_show_hidden  = ${ 'true' if show_hidden  == True else ( 'null' if show_hidden  == None else 'false' ) },

        user    = ${ get_current_user() },
        history = ${ get_history( history.id ) },
        hdas    = ${ get_hdas( history.id, datasets ) };

    // add user data to history
    // i don't like this history+user relationship, but user authentication changes views/behaviour
    history.user = user;

    // create the history panel
    var historyPanel = new HistoryPanel({
        model           : new History( history, hdas ),
        urlTemplates    : galaxy_paths.attributes,
        logger          : ( debugging )?( console ):( null ),
        // is page sending in show settings? if so override history's
        show_deleted    : page_show_deleted,
        show_hidden     : page_show_hidden
    });
    historyPanel.render();

    // ...or LOAD FROM THE API
    //historyPanel = new HistoryPanel({
    //    model: new History(),
    //    urlTemplates    : galaxy_paths.attributes,
    //    logger          : ( debugging )?( console ):( null ),
    //    // is page sending in show settings? if so override history's
    //    show_deleted    : page_show_deleted,
    //    show_hidden     : page_show_hidden
    //});
    //historyPanel.model.loadFromApi( history.id );

    // set it up to be accessible across iframes
    //TODO:?? mem leak
    top.Galaxy.currHistoryPanel = historyPanel;
    var currUser = new User( user );
    if( !Galaxy.currUser ){ Galaxy.currUser = currUser; }

    // QUOTA METER is a cross-frame ui element (meter in masthead, over quota message in history)
    //  create it and join them here for now (via events)
    //TODO: this really belongs in the masthead
    //TODO: and the quota message (curr. in the history panel) belongs somewhere else

    //window.currUser.logger = console;
    var quotaMeter = new UserQuotaMeter({
        model   : currUser,
        //logger  : ( debugging )?( console ):( null ),
        el      : $( top.document ).find( '.quota-meter-container' )
    });
    //quotaMeter.logger = console; window.quotaMeter = quotaMeter
    quotaMeter.render();

    // show/hide the 'over quota message' in the history when the meter tells it to
    quotaMeter.bind( 'quota:over',  historyPanel.showQuotaMessage, historyPanel );
    quotaMeter.bind( 'quota:under', historyPanel.hideQuotaMessage, historyPanel );
    // having to add this to handle re-render of hview while overquota (the above do not fire)
    historyPanel.on( 'rendered rendered:initial', function(){
        if( quotaMeter.isOverQuota() ){
            historyPanel.showQuotaMessage();
        }
    });
    //TODO: this _is_ sent to the page (over_quota)...

    // update the quota meter when current history changes size
    historyPanel.model.bind( 'change:nice_size', function(){
        quotaMeter.update()
    }, quotaMeter );


    //ANOTHER cross-frame element is the history-options-button...
    // in this case, we need to change the popupmenu options listed to include some functions for this history
    // these include: current (1 & 2) 'show/hide' delete and hidden functions, and (3) the collapse all option
    (function(){
        // don't try this if the history panel is in it's own window
        if( top.document === window.document ){
            return;
        }

        // lots of wtf here...due to infernalframes
        //TODO: this is way tooo acrobatic
        var $historyButtonWindow = $( top.document ),
            HISTORY_MENU_BUTTON_ID = 'history-options-button',
            $historyMenuButton = $historyButtonWindow.find( '#' + HISTORY_MENU_BUTTON_ID ),
            // jq data in another frame can only be accessed by the jQuery in that frame,
            //  get the jQuery from the top frame (that contains the history-options-button)
            START_INSERTING_AT_INDEX = 11,
            COLLAPSE_OPTION_TEXT = _l("Collapse Expanded Datasets"),
            DELETED_OPTION_TEXT  = _l("Include Deleted Datasets"),
            HIDDEN_OPTION_TEXT   = _l("Include Hidden Datasets");
            windowJQ = $( top )[0].jQuery,
            popupMenu = ( windowJQ && $historyMenuButton[0] )?( windowJQ.data( $historyMenuButton[0], 'PopupMenu' ) )
                                                             :( null );

        //console.debug(
        //    '$historyButtonWindow:', $historyButtonWindow,
        //    '$historyMenuButton:', $historyMenuButton,
        //    'windowJQ:', windowJQ,
        //    'popupmenu:', popupMenu
        //);
        if( !popupMenu ){ return; }

        // since the history frame reloads so often (compared to the main window),
        //  we need to check whether these options are there already before we add them again
        // In IE, however, NOT re-adding them creates a 'cant execute from freed script' error:
        //  so...we need to re-add the function in either case (just not the option itself)
        //NOTE: we use the global Galaxy.currHistoryPanel here
        //  because these remain bound in the main window even if panel refreshes
        //TODO: too much boilerplate
        //TODO: ugh...(in general)
        var collapseOption = popupMenu.findItemByHtml( COLLAPSE_OPTION_TEXT );
        if( !collapseOption ){
            collapseOption = {
                html    : COLLAPSE_OPTION_TEXT
            };
            popupMenu.addItem( collapseOption, START_INSERTING_AT_INDEX )
        }
        collapseOption.func = function() {
            Galaxy.currHistoryPanel.collapseAllHdaBodies();
        };

        var deletedOption = popupMenu.findItemByHtml( DELETED_OPTION_TEXT );
        if( !deletedOption ){
            deletedOption = {
                html    : DELETED_OPTION_TEXT
            };
            popupMenu.addItem( deletedOption, START_INSERTING_AT_INDEX + 1 )
        }
        deletedOption.func = function( clickEvent, thisMenuOption ){
            var show_deleted = Galaxy.currHistoryPanel.toggleShowDeleted();
            thisMenuOption.checked = show_deleted;
        };
        // whether was there or added, update the checked option to reflect the panel's settings on the panel render
        deletedOption.checked = Galaxy.currHistoryPanel.storage.get( 'show_deleted' );

        var hiddenOption = popupMenu.findItemByHtml( HIDDEN_OPTION_TEXT );
        if( !hiddenOption ){
            hiddenOption = {
                html    : HIDDEN_OPTION_TEXT
            };
            popupMenu.addItem( hiddenOption, START_INSERTING_AT_INDEX + 2 )
        }
        hiddenOption.func = function( clickEvent, thisMenuOption ){
            var show_hidden = Galaxy.currHistoryPanel.toggleShowHidden();
            thisMenuOption.checked = show_hidden;
        };
        // whether was there or added, update the checked option to reflect the panel's settings on the panel render
        hiddenOption.checked = Galaxy.currHistoryPanel.storage.get( 'show_hidden' );
    })();

    //TODO: both the quota meter and the options-menu stuff need to be moved out when iframes are removed

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
        .historyItemBody {
            display: none;
        }

        #history-controls {
            /*border: 1px solid white;*/
            margin-bottom: 5px;
            padding: 5px;
        }

        #history-title-area {
            margin: 0px 0px 5px 0px;
            /*border: 1px solid red;*/
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
            /*color: gray;*/
        }

        #quota-message-container {
            margin: 8px 0px 5px 0px;
        }
        #quota-message {
            margin: 0px;
        }

        #history-subtitle-area {
            /*border: 1px solid green;*/
        }
        #history-size {
        }
        #history-secondary-links {
        }

        /*why this is getting underlined is beyond me*/
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

        .historyItemTitle {
            text-decoration: underline;
            cursor: pointer;
        }
        .historyItemTitle:hover {
            text-decoration: underline;
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

<body class="historyPage"></body>
