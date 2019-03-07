<%inherit file="/display_base.mako"/>

<%def name="javascript_app()">

    ${parent.javascript_app()}

    <script type="text/javascript">
        config.addInitialization(function() {
            console.log("page/display.mako, javascript_app", "Setup embedded content");
            // Setup embedded content:
            //  (a) toggles for showing/hiding embedded content;
            //  (b) ...
            $('.embedded-item').each( function() {
                var container = $(this);
                if( container.hasClass( 'history' ) ){ return; }
                //note: we can't do the same override for visualizations
                // bc builtins (like trackster) need the handlers/ajax below to work.
                // instead: (for registry visualizations) we'll clear the handlers below
                //  and add new ones (in embed_in_frame.mako) ...ugh.
            
                // Show embedded item.
                var show_embedded_item = function() {
                    var ajax_url = container.find("input[type=hidden]").val();
                    // Only get item content if it's not already there.
                    var item_content = $.trim(container.find(".item-content").text());
                    if (!item_content) {
                        $.ajax({
                            type: "GET",
                            url: ajax_url,
                            error: function() { alert("Getting item content failed."); },
                            success: function( item_content ) {
                                container.find(".summary-content").hide("fast");
                                container.find(".item-content").html(item_content);
                                container.find(".expanded-content").show("fast");
                                container.find(".toggle-expand").hide();
                                container.find(".toggle").show();

                                window.bundleEntries.make_popup_menus();
                            }
                        });
                    } else {
                        container.find(".summary-content").hide("fast");
                        container.find(".expanded-content").show("fast");
                        container.find(".toggle-expand").hide();
                        container.find(".toggle").show();
                    }
                };
            
                // Hide embedded item.
                var hide_embedded_item = function() {
                    container.find(".expanded-content").hide("fast");
                    container.find(".summary-content").show("fast");
                    container.find(".toggle").hide();
                    container.find(".toggle-expand").show();
                };
            
                // Setup toggle expand.
                var toggle_expand = $(this).find('.toggle-expand');
                toggle_expand.click( function() {
                    show_embedded_item();
                    return false;
                });
            
                // Setup toggle contract.
                var toggle_contract = $(this).find('.toggle');
                toggle_contract.click( function() {
                    hide_embedded_item();
                    return false;
                });
            
                // Setup toggle embed.
                var toggle_embed = $(this).find('.toggle-embed');
                toggle_embed.click( function() {
                    if (container.find(".expanded-content").is(":visible")) {
                        hide_embedded_item();
                    } else {
                        show_embedded_item();
                    }
                    return false;
                });
            });
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
