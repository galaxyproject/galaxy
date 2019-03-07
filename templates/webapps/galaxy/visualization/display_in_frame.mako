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
    ${h.css(
        "trackster"
    )}

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
    <a href="${h.url_for( controller='/visualization', action='imp', id=trans.security.encode_id( visualization.id ) )}"
        class="btn btn-secondary fa fa-plus float-right"
        title="Import visualization"></a>
</%def>

<%def name="render_item( visualization, config )">
    <div id="${trans.security.encode_id( visualization.id )}" class="unified-panel-body" style="overflow:none;top:0px;">
        <iframe frameborder="0" width="100%" height="100%" sandbox="allow-forms allow-same-origin allow-scripts"
                src="/visualization/saved?id=${encoded_visualization_id}&embedded=True">
        </iframe>
    </div>
</%def>
