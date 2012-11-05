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
## all the possible history urls (primarily from web controllers at this point)
<%def name="get_history_url_templates()">
<%
    from urllib import unquote_plus

    history_class_name      = history.__class__.__name__
    encoded_id_template     = '<%= id %>'

    url_dict = {
        # TODO:?? next 3 needed?
        'base'          : h.url_for( controller="/history" ),
        ##TODO: move these into the historyMV
        'hide_deleted'  : h.url_for( controller="/history", show_deleted=False ),
        'hide_hidden'   : h.url_for( controller="/history", show_hidden=False ),

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
        'purge' : h.url_for( controller='dataset', action='purge',
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
        #TODO: show deleted handled by history
        'delete' : h.url_for( controller='dataset', action='delete',
            dataset_id=encoded_id_template, show_deleted_on_refresh=show_deleted ),

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
    return trans.webapp.api_controllers[ 'histories' ].show( trans, trans.security.encode_id( id ) )
%>
</%def>

<%def name="get_current_user()">
<%
    return trans.webapp.api_controllers[ 'users' ].show( trans, 'current' )
%>
</%def>

<%def name="get_hdas( history_id, hdas )">
<%
    #BUG: one inaccessible dataset will error entire list

    if not hdas:
        return '[]'
    # rather just use the history.id (wo the datasets), but...
    return trans.webapp.api_controllers[ 'history_contents' ].index(
        #trans, trans.security.encode_id( history_id ),
        trans, trans.security.encode_id( history_id ),
        ids=( ','.join([ trans.security.encode_id( hda.id ) for hda in hdas ]) ) )
%>
</%def>


## -----------------------------------------------------------------------------
<%def name="javascripts()">
${parent.javascripts()}

${h.js(
    "libs/jquery/jstorage",
    "libs/jquery/jquery.autocomplete", "galaxy.autocom_tagging",
    "libs/json2",
    "libs/backbone/backbone-relational",
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
    
    "template-history-historyPanel",

    "template-user-quotaMeter-quota",
    "template-user-quotaMeter-usage"
)}

##TODO: fix: curr hasta be _after_ h.templates - move somehow
${h.js(
    "mvc/history",
    ##"mvc/tags", "mvc/annotations",
    "mvc/user/user-model", "mvc/user/user-quotameter"
)}
    
<script type="text/javascript">
// set js localizable strings
GalaxyLocalization.setLocalizedString( ${ create_localization_json( get_page_localized_strings() ) } );

// add needed controller urls to GalaxyPaths
galaxy_paths.set( 'hda', ${get_hda_url_templates()} );
galaxy_paths.set( 'history', ${get_history_url_templates()} );

$(function(){

    // ostensibly, this is the App
    if( console && console.debug ){
        //if( console.clear ){ console.clear(); }
        console.debug( 'using backbone.js in history panel' );
        console.pretty = function( o ){ $( '<pre/>' ).text( JSON.stringify( o, null, ' ' ) ).appendTo( 'body' ); }
    }


    // load initial data in this page - since we're already sending it...
    var user    = ${ get_current_user() },
        history = ${ get_history( history.id ) },
        hdas    = ${ get_hdas( history.id, datasets ) };
    console.debug( 'user:', user );
    console.debug( 'history:', history );
    console.debug( 'hdas:', hdas );

    // i don't like this relationship, but user authentication changes views/behaviour
    history.user = user;
    history.show_deleted = ${ 'true' if show_deleted else 'false' };
    history.show_hidden  = ${ 'true' if show_hidden  else 'false' };

    //console.debug( 'galaxy_paths:', galaxy_paths );
    var glx_history = new History( history, hdas );
    glx_history.logger = console;

    var glx_history_view = new HistoryView({
        model: glx_history,
        urlTemplates: galaxy_paths.attributes,
        logger: console
    });
    glx_history_view.render();


    // ...OR load from the api
    //var glx_history = new History().setPaths( galaxy_paths ),
    //    glx_history_view = new HistoryView({ model: glx_history });
    //console.warn( 'fetching' );
    //glx_history.loadFromApi( pageData.history.id );

    
    // quota meter is a cross-frame ui element (meter in masthead, over quota message in history)
    //  create it and join them here for now (via events)
    window.currUser = new User( user );
    //window.currUser.logger = console;
    window.quotaMeter = new UserQuotaMeter({ model: currUser, el: $( top.document ).find( '.quota-meter-container' ) });
    window.quotaMeter.render();
    //window.quotaMeter.logger = console;

    // show/hide the 'over quota message' in the history when the meter tells it to
    quotaMeter.bind( 'quota:over',  glx_history_view.showQuotaMessage, glx_history_view );
    quotaMeter.bind( 'quota:under', glx_history_view.hideQuotaMessage, glx_history_view );
    // having to add this to handle re-render of hview while overquota (the above do not fire)
    glx_history_view.on( 'rendered', function(){
        if( window.quotaMeter.isOverQuota() ){
            glx_history_view.showQuotaMessage();
        }
    });

    // update the quota meter when any hda reaches a 'final' state
    //NOTE: use an anon function or update will be passed the hda and think it's the options param
    glx_history_view.on( 'hda:rendered:final', function(){ window.quotaMeter.update({}) }, window.quotaMeter )


    if( console && console.debug ){
        window.user = top.user = user;
        window._history = top._history = history;
        window.hdas = top.hdas = hdas;
        window.glx_history = top.glx_history = glx_history;
        window.glx_history_view = top.glx_history_view = glx_history_view;
        top.storage = jQuery.jStorage
    }

    return;
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

<body class="historyPage"></body>
