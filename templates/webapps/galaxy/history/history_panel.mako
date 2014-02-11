<%namespace file="/utils/localization.mako" import="localize_js_strings" />

## ----------------------------------------------------------------------------
<%def name="current_history_panel( selector_to_attach_to=None, show_deleted=None, show_hidden=None, hda_id=None )">

${history_panel_javascripts()}

<script type="text/javascript">
onhistoryready.done( function( historyPanel ){
    // attach a panel to selector_to_attach_to and load the current history/hdas over the api
    var currPanel = new historyPanel.HistoryPanel({
        // is page sending in show settings? if so override history's
        show_deleted    : ${ 'true' if show_deleted == True else ( 'null' if show_deleted == None else 'false' ) },
        show_hidden     : ${ 'true' if show_hidden  == True else ( 'null' if show_hidden  == None else 'false' ) },
        el              : $( "${selector_to_attach_to}" ),
        linkTarget      : 'galaxy_main',
        onready         : function loadAsCurrentHistoryPanel(){
            var panel = this;
            this.connectToQuotaMeter( Galaxy.quotaMeter ).connectToOptionsMenu( Galaxy.historyOptionsMenu );
            this.loadCurrentHistory()
                .fail( function(){
                    panel.render();
                });
            }
    });
    Galaxy.currHistoryPanel = currPanel;
});
</script>
</%def>


## ----------------------------------------------------------------------------
<%def name="history_panel( history_id, selector_to_attach_to=None, \
                           show_deleted=None, show_hidden=None, hda_id=None )">

${history_panel_javascripts()}

<script type="text/javascript">
onhistoryready.done( function( historyPanel ){
    // attach a panel to selector_to_attach_to and load the history/hdas with the given history_id over the api
    var panel = new historyPanel.HistoryPanel({
        show_deleted    : ${ 'true' if show_deleted == True else ( 'null' if show_deleted == None else 'false' ) },
        show_hidden     : ${ 'true' if show_hidden  == True else ( 'null' if show_hidden  == None else 'false' ) },
        el              : $( "${selector_to_attach_to}" ),
        onready         : function loadHistoryById(){
            var panel = this;
            this.loadHistoryWithHDADetails( '${history_id}' )
                .fail( function(){
                    panel.render();
                });
            }
    });
});
</script>
</%def>


## ----------------------------------------------------------------------------
<%def name="bootstrapped_history_panel( history, hdas, selector_to_attach_to=None, \
                                        show_deleted=None, show_hidden=None, hda_id=None )">

${history_panel_javascripts()}

<script type="text/javascript">
onhistoryready.done( function( historyPanel ){
    // attach a panel to selector_to_attach_to and use a history model with bootstrapped data

    // history module is already in the dpn chain from the panel. We can re-scope it here.
    var historyModel = require( 'mvc/history/history-model' ),
        debugging = JSON.parse( sessionStorage.getItem( 'debugging' ) ) || false,
        historyJSON = ${h.to_json_string( history )},
        hdaJSON = ${h.to_json_string( hdas )};

    var history = new historyModel.History( historyJSON, hdaJSON, {
        logger: ( debugging )?( console ):( null )
    });

    var panel = new historyPanel.HistoryPanel({
        show_deleted    : ${ 'true' if show_deleted == True else ( 'null' if show_deleted == None else 'false' ) },
        show_hidden     : ${ 'true' if show_hidden  == True else ( 'null' if show_hidden  == None else 'false' ) },
        el              : $( "${selector_to_attach_to}" ),
        model           : history,
        onready         : function(){ this.render(); }
    });
})
</script>
</%def>


## ----------------------------------------------------------------------------- generic 'base' function
<%def name="history_panel_javascripts()">
${h.js(
    "utils/localization",
    "mvc/base-mvc",
    "mvc/tags",
    "mvc/annotations"
)}

##TODO: concat these
${h.templates(
    "history-templates",
    "helpers-common-templates"
)}

${localize_js_strings([
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
    'Error: unknown dataset state'
])}

<script type="text/javascript">
var debugging = JSON.parse( sessionStorage.getItem( 'debugging' ) ) || false,
    // use deferred to allow multiple callbacks (.done())
    onhistoryready = jQuery.Deferred();

require.config({
    baseUrl : "${h.url_for( '/static/scripts' )}"
});

// requirejs optimizer:
   //r.js -o baseUrl='/Users/carleberhard/galaxy/iframe-2-hpanel/static/scripts' \
   //        name=./mvc/history/history-panel.js out=history-panel.min.js
//TODO: can't get either to work - historyPanel is undefined
//require([ "history-panel.min" ], function( historyPanel ){
//require([ "/static/scripts/history-panel.min.js" ], function( historyPanel ){

require([ "mvc/history/history-panel" ], function( historyPanel ){
    $(function(){
        onhistoryready.resolve( historyPanel )
    });
});
</script>
</%def>
