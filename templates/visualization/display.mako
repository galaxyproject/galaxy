<%inherit file="/display_base.mako"/>

<%def name="javascripts()">
    <% config = item_data %>
    ${parent.javascripts()}
    ${h.js( "jquery.event.drag", "jquery.autocomplete", "jquery.mousewheel", "trackster" )}
    
    <script type="text/javascript">
        var view;
        // To adjust the size of the viewport to fit the fixed-height footer
        var refresh = function( e ) {
            if (view !== undefined) {
                view.viewport_container.height( $(window).height() - 100 );
                view.nav_container.width( $("#center").width() );
                view.redraw();
            }
        };
        $(window).bind( "resize", function(e) { refresh(e); } );
        $("#right-border").bind( "click dragend", function(e) { refresh(e); } );
        $(window).trigger( "resize" );
    </script>
    
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}

    <style type="text/css">
        .nav-container {
            position: fixed;
            width: 100%;
            left: 0;
            bottom: 0;
        }
        .page-body {
            padding: 0px;
        }

    </style>
</%def>

<%def name="render_item_header( item )">
    ## Don't need to show header
</%def>

<%def name="render_item_links( visualization )">
    
</%def>

<%def name="render_item( visualization, config )">
    <div id="${visualization.id}"></div>

    <script type="text/javascript">

        var data_url = "${h.url_for( controller='/tracks', action='data' )}",
            reference_url = "${h.url_for( controller='/tracks', action='reference' )}",
            chrom_url = "${h.url_for( controller='/tracks', action='chroms' )}",
            view;

        var container_element = $("#${visualization.id}");
        view = new View( container_element, "${config.get('chrom')}", "${config.get('title') | h}", "${config.get('vis_id')}", "${config.get('dbkey')}" );
        %for track in config.get('tracks'):
            view.add_track(
                new ${track["track_type"]}( "${track['name'] | h}", view, ${track['dataset_id']}, ${track['prefs']} )
            );
        %endfor

    </script>
</%def>