<%inherit file="/webapps/galaxy/base_panels.mako"/>
<%namespace file="/galaxy_client_app.mako" name="galaxy_client"/>

<%def name="title()">
    ${_('Histories')}
</%def>

## ----------------------------------------------------------------------------
<%!
    column_width = 312
    border_width = 1
    column_gap = 8

    header_height = 29
    footer_height = 0

    controls_height = 20
%>

## ----------------------------------------------------------------------------
<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style type="text/css">
    html, body {
        margin: 0px;
        padding: 0px;
    }

    .flex-row-container,
    .flex-column-container {
        display: -webkit-box;
        display: -webkit-flex;
        display: -ms-flexbox;
        display: flex;

        /* force ff to squish beyond content:
           https://developer.mozilla.org/en-US/Firefox/Releases/34/Site_Compatibility#CSS */
        min-width: 0px;
        min-height: 0px;

        -webkit-align-items: stretch;
        -ms-align-items: stretch;
        align-items: stretch;

        -webkit-align-content: stretch;
        -ms-align-content: stretch;
        align-content: stretch;

        -webkit-justify-content: flex-start;
        -ms-flex-pack: start;
        justify-content: flex-start;
    }
    .flex-row-container {
        -webkit-flex-direction: column;
        -ms-flex-direction: column;
        flex-direction: column;
    }
    .flex-column-container {
        -webkit-flex-direction: row;
        -ms-flex-direction: row;
        flex-direction: row;
    }
    .flex-row,
    .flex-column {
        -webkit-flex: 1 1 auto;
        -ms-flex: 1 1 auto;
        flex: 1 1 auto;

        -webkit-align-self: auto;
        -ms-flex-item-align: auto;
        align-self: auto;
    }
    .flex-row {
    }
    .flex-column {
    }

    .header, .footer {
        width: 100%;
    }

    .header {
        background-color: lightgrey;
        min-height: ${header_height}px;
        max-height: ${header_height}px;
    }
    .header-control {
        margin-top: 4px;
    }
    .header-control-right,
    .header-control-left {
        margin-right: 8px;
        margin-left: 8px;
    }

    .header-control-left > * {
        margin: 0px 4px 4px 0px;
    }

    .header-control-center {
        text-align: center;
        max-height: 22px;
        -webkit-flex: 0 1 auto;
        -ms-flex: 0 1 auto;
        flex: 0 1 auto;

        /* truncate */
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-height: 22px;
    }
    .header-info {
        display: inline-block;
        padding: 2px 4px 2px 4px;
        color: grey;

    }

    .header-control-right {
        text-align: right;
    }
    .header-control-right > * {
        margin: 0px 0px 4px 4px;
    }

    .header-search {
        display: inline-block;
    }
    .header-search .search-clear,
    .header-search .search-loading {
        margin-top: -22px;
    }
    .header input.search-query {
        font-size: 90%;
        height: 21px;
        padding: 2px;
    }

    .outer-middle {
        overflow: auto;
    }
    .middle {
        min-width: 100%;
        margin: 0px 0px 0px 0px;
        background-color: white;
        padding: ${column_gap}px;
    }

    .history-column {
        width: ${column_width}px;
        margin: 0px ${column_gap}px 0px 0px;
    }
    .history-column:last-child {
        margin-right: 0px;
    }

    .panel-controls {
        width: 100%;
        height: ${controls_height}px;
        border-radius: 3px;
        background-color: white;
        text-align: center;

        flex: 0 0 auto;

        -webkit-align-self: auto;
        -ms-flex-item-align: auto;
        align-self: auto;
    }
    .header .btn,
    .panel-controls .btn {
        height: ${controls_height}px;
        line-height: ${controls_height - 2}px;
        font-size: 90%;
        padding-top: 0px;
        padding-bottom: 0px;
    }
    .panel-controls .pull-left .btn {
        margin-right: 4px;
    }
    .panel-controls .pull-right .btn {
        margin-left: 4px;
    }

    .footer {
        min-height: ${footer_height}px;
        max-height: ${footer_height}px;
        background-color: grey;
    }

    /* ---- columns */
    .history-panel {
        width: 100%;
        margin-top: 4px;

        border: ${border_width}px solid grey;
        border-radius: 3px;
        background-color: #DFE5F9;
        
        overflow: auto;
    }

    .history-column:first-child {
        position: fixed;
        z-index : 1;
    }
    .history-column:first-child .history-panel {
        border: 1px solid black;
        box-shadow: 4px 4px 4px rgba( 96, 96, 96, 0.3 );
    }

    .history-column:nth-child(2) {
        margin-left: ${( column_width + column_gap )}px;
    }

    .loading-overlay {
        display: none;
        position: absolute;
        height: 100%;
        width: 100%;
        background-color: red;
        opacity: 0.75;
        z-index: 2;
        text-align: center;
    }
    .loading-overlay-message {
        margin-top: 6px;
        font-style: italic;
        vertical-align: middle;
    }

    </style>

</%def>


## ----------------------------------------------------------------------------
<%def name="center_panel()"></%def>

<%def name="javascript_app()">
<script type="text/javascript">
define( 'app', function(){
    require([
        'mvc/history/history-model',
        'mvc/history/multi-panel'
    ], function( HISTORY_MODEL, MULTI_PANEL ){
        $(function(){
            $( '#center' ).addClass( 'flex-row-container' );
            window.historyJSONArray = bootstrapped.historyJSONArray;

            var historyModels = [];
            historyJSONArray.forEach( function( historyJSON ){
                if( !historyJSON.purged ){
                    historyModels.push( new HISTORY_MODEL.History( historyJSON ) );
                }
            });
            histories = new HISTORY_MODEL.HistoryCollection( historyModels, {
                includeDeleted : bootstrapped.includingDeleted
            });
            multipanel = new MULTI_PANEL.MultiPanelColumns({
                el                          : $( '#center' ),
                histories                   : histories,
                //historiesJSON            : historiesJSON,
                order                       : bootstrapped.order,
                currentHistoryId            : '${current_history_id}'
            }).render( 0 );
        });
    });
});
</script>
${ galaxy_client.load( app='app', historyJSONArray=histories,
    includingDeleted=include_deleted_histories, order=order ) }
</%def>
