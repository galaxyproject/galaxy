<%inherit file="/display_base.mako"/>

<%def name="javascripts()">
    <% config = item_data %>
    ${parent.javascripts()}
    
    <!--[if lt IE 9]>
      <script type='text/javascript' src="${h.url_for('/static/scripts/excanvas.js')}"></script>
    <![endif]-->
    
    ${h.js( "jquery.event.drag", "jquery.autocomplete", "trackster" )}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}

    <style type="text/css">
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
    <div id="${visualization.id}" class="unified-panel-body" style="overflow:none;top:0px;"></div>

    <script type="text/javascript">

        var data_url = "${h.url_for( controller='/tracks', action='data' )}",
            reference_url = "${h.url_for( controller='/tracks', action='reference' )}",
            chrom_url = "${h.url_for( controller='/tracks', action='chroms' )}",
            view,
            container_element = $("#${visualization.id}");
        
        $(function() {
            
            if (container_element.parents(".item-content").length > 0) { // Embedded viz
                container_element.parents(".item-content").css( { "max-height": "none", "overflow": "visible" } );
            } else { // Viewing just one shared viz
                $("#right-border").live("click", function() { view.resize_window(); });
            }
            view = new View( container_element, "${config.get('title') | h}", "${config.get('vis_id')}", "${config.get('dbkey')}" );
            %for track in config.get('tracks'):
                view.add_track(
                    new ${track["track_type"]}( "${track['name'] | h}", view, ${track['dataset_id']}, ${track['prefs']} )
                );
            %endfor
        });

    </script>
</%def>