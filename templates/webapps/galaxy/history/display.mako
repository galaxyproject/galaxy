<%inherit file="/display_base.mako"/>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

<%def name="render_item_links( history )">
</%def>

<%def name="render_item_header( item )">
</%def>

<%def name="render_item( item, item_data )">
    <% history_id = trans.security.encode_id(item.id) %>
    <div id="history-${ history_id }"></div>
    <script type="text/javascript">
        config.addInitialization(function(galaxy, config) {
            console.log("display.mako render_item");
            window.bundleEntries.mountHistory("#history-${ history_id }", { id: "${ history_id }" });
        });
    </script>
</%def>
