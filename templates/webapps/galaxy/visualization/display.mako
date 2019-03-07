<%inherit file="/display_base.mako"/>

<%def name="javascripts()">
    <% config = item_data %>
    ${parent.javascripts()}

    <script type='text/javascript'>
        $(function() {
            // HACK: add bookmarks container and header.
            $('#right > .unified-panel-body > div').append(
                $('<div/>').attr('id', 'bookmarks-container')
                .append( $('<h4/>').text('Bookmarks') )
            );
        });
    </script>

</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css("trackster")}

    ## Style changes needed for display.
    <style type="text/css">
        .page-body {
            padding: 0px;
        }
        #bookmarks-container {
            padding-left: 10px;
        }
        .bookmark {
            margin: 0em;
        }
    </style>
</%def>

<%def name="render_item_header( item )">
    ## Don't need to show header
</%def>

<%def name="render_item_links( visualization )">
    <a
        href="${h.url_for( controller='/visualization', action='imp', id=trans.security.encode_id( visualization.id ) )}"
        class="btn btn-secondary fa fa-plus float-right"
        title="Import visualization"></a>
</%def>

<%def name="render_item( visualization, config )">
    <div id="${trans.security.encode_id( visualization.id )}" class="unified-panel-body" style="overflow:none;top:0px;"></div>

    <script type="text/javascript">
        // FIXME: deliberate global required for now due to requireJS integration.
        view = null;

        var ui = new (window.bundleEntries.TracksterUI)( "${h.url_for('/')}" );
        var container_element = $("#${trans.security.encode_id( visualization.id )}");

        $(function() {
            var is_embedded = (container_element.parents(".item-content").length > 0);

            // HTML setup.
            if (is_embedded) {
                container_element.css( { "position": "relative" } );
            } else { // Viewing just one shared viz
                $("#right-border").click(function() { view.resize_window(); });
            }

            // Create visualization.
            var callback;
            %if 'viewport' in config:
                var callback = function() { view.change_chrom( '${config['viewport']['chrom']}', ${config['viewport']['start']}, ${config['viewport']['end']} ); }
            %endif
            view = ui.create_visualization( {
                                            container: container_element,
                                            name: "${config.get('title') | h}",
                                            vis_id: "${config.get('vis_id')}",
                                            dbkey: "${config.get('dbkey')}"
                                         },
                                         ${ h.dumps( config.get( 'viewport', dict() ) ) },
                                         ${ h.dumps( config['tracks'] ) },
                                         ${ h.dumps( config.get('bookmarks') ) }
                                         );

            // Set up keyboard navigation.
            ui.init_keyboard_nav(view);

            // HACK: set viewport height because it cannot be set automatically. Currently, max height for embedded
            // elts is 25em, so use 20em.
            view.viewport_container.height("20em");
        });

    </script>
</%def>
