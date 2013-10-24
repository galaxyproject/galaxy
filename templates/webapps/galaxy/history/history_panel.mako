<%namespace file="/utils/localization.mako" import="localize_js_strings" />

## ---------------------------------------------------------------------------------------------------------------------
<%def name="history_panel_stylesheets()">
    <style>
        ## TODO: move to base.less
        /*---- page level */
        [class$="messagesmall"] {
            margin: 0px 8px 8px 8px;
        }
        #message-container  {
            cursor: pointer;
        }
        #message-container [class$=message] {
            margin: 8px 0px 0px 0px;
        }

        /*---- history level */
        #history-controls {
            margin: 0px;
            padding: 10px;
        }

        #history-title-area {
            margin: 0px 0px 4px 0px;
        }
        #history-name {
            word-wrap: break-word;
            font-weight: bold;
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
        .historyItem [class$=messagesmall] {
            margin: 0px 0px 4px 0px;
            border: 1px solid grey;
            font-size: 90%;
        }

        div.historyItemWrapper {
            margin: 0px;
            padding: 8px 10px 8px 10px;
        }
        .historyItemTitle {
            text-decoration: underline;
            cursor: pointer;
        }
        .historyItemTitle:hover {
            text-decoration: underline;
        }
        .historyItemBody {
            display: none;
        }

    </style>
</%def>


## ----------------------------------------------------------------------------
<%def name="current_history_panel( selector_to_attach_to=None, show_deleted=None, show_hidden=None, hda_id=None )">
<script type="text/javascript">
function onModuleReady( historyPanel ){
    // attach a panel to selector_to_attach_to and load the current history/hdas over the api

    var currPanel = new historyPanel.HistoryPanel({
        // is page sending in show settings? if so override history's
        show_deleted    : ${ 'true' if show_deleted == True else ( 'null' if show_deleted == None else 'false' ) },
        show_hidden     : ${ 'true' if show_hidden  == True else ( 'null' if show_hidden  == None else 'false' ) },
        el              : $( "${selector_to_attach_to}" ),
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
}
</script>

${history_panel_javascripts()}
</%def>


## ----------------------------------------------------------------------------
<%def name="history_panel( history_id, selector_to_attach_to=None, \
                           show_deleted=None, show_hidden=None, hda_id=None )">
<script type="text/javascript">
function onModuleReady( historyPanel ){
    // attach a panel to selector_to_attach_to and load the history/hdas with the given history_id over the api

    var panel = new historyPanel.HistoryPanel({
        show_deleted    : ${ 'true' if show_deleted == True else ( 'null' if show_deleted == None else 'false' ) },
        show_hidden     : ${ 'true' if show_hidden  == True else ( 'null' if show_hidden  == None else 'false' ) },
        el              : $( "${selector_to_attach_to}" ),
        onready         : function loadHistoryById(){
            var panel = this;
            this.loadHistoryWithDetails( '${history_id}' )
                .fail( function(){
                    panel.render();
                });
            }
    });
</script>

${history_panel_javascripts()}
</%def>


## ----------------------------------------------------------------------------
<%def name="bootstrapped_history_panel( history, hdas, selector_to_attach_to=None, \
                                        show_deleted=None, show_hidden=None, hda_id=None )">
<script type="text/javascript">
function onModuleReady( historyPanel ){
    // attach a panel to selector_to_attach_to and use a history model with bootstrapped data

    // history module is already in the dpn chain from the panel. We can re-scope it here.
    var historyModel = require( 'mvc/history/history-model' ),
        debugging = JSON.parse( sessionStorage.getItem( 'debugging' ) ) || false,
        historyJSON = ${h.to_json_string( history )},
        hdaJSON = ${h.to_json_string( hdas )};

    // i don't like this history+user relationship, but user authentication changes views/behaviour
    historyJSON.user = Galaxy.currUser.toJSON();

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
}
</script>

${history_panel_javascripts()}
</%def>


## ----------------------------------------------------------------------------- generic 'base' function
<%def name="history_panel_javascripts()">
${h.js(
    "libs/jquery/jquery.autocomplete", "galaxy.autocom_tagging"
)}

##TODO: concat these
${h.templates(
    "history-templates"
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
var debugging = JSON.parse( sessionStorage.getItem( 'debugging' ) ) || false;

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
    onModuleReady( historyPanel );
});
</script>
</%def>


