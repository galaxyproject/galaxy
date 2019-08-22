<%inherit file="/display_base.mako"/>

<%def name="javascript_app()">

    ${parent.javascript_app()}

    <script type="text/javascript">
        config.addInitialization(function() {
            console.log("page/display.mako, javascript_app", "Setup embedded content");
            window.bundleEntries.render_embedded_items();
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "base" )}
    <style type="text/css">
        .toggle { display: none; }
        .embedded-item .title {
            padding-top: 1px;
        }
        .embedded-item h4 {
            margin: 0px;
        }
        ## Format tables in pages so that they look like they do in the page editor.
        .page-body > table {
            padding: 8px 5px 5px;
            min-width: 500px; 
            border: none;
            margin-top: 1em;
            margin-bottom: 1em;
        }
        .page-body caption { 
            text-align: left;
            background: #E4E4B0; 
            padding: 5px; 
            font-weight: bold; 
        }
        .page-body > table td {
            width: 25%;
            padding: 0.2em 0.8em;
        }
        ## HACKs to get Trackster navigation controls to display.
        .embedded-item .trackster-nav-container {
            height: inherit;
        }
        .embedded-item .trackster-nav {
            position: inherit;
        }

        /* ---------------------------- histories */
        .embedded-item.history .toggle {
            display: inline;
        }
        /** wraps around the history */
        .embedded-item.history .item-content {
            background-color: white;
            padding: 8px;
            border-radius: 0px 0px 4px 4px;
        }
        .embedded-item.history .history-panel .datasets-list {
            margin-bottom: 8px;
        }
        .embedded-item.history .history-panel .errormessage {
            margin-top: 8px;
        }
        .annotated-history-panel .history-controls {
            margin: 0px 0px 16px 0px;
        }

        /* ---------------------------- visualizations */
        .embedded-item.visualization .item-content {
            max-height: none;
        }
    </style>
</%def>

<%def name="render_item_header( item )">
    ## No header for pages.
</%def>

<%def name="render_item_links( page )">
</%def>

<%def name="render_item( page, page_data=None )">
    ${page_data}
</%def>
