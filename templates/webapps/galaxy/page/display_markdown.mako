<%inherit file="/display_base.mako"/>

<%def name="javascript_app()">

    ${parent.javascript_app()}

    <script type="text/javascript">
        config.addInitialization(function() {
            console.log("page/display_markdown.mako, javascript_app", "Setup page display markdown");
            window.bundleEntries.mountPageDisplay();
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "base" )}
</%def>

<%def name="render_item_header( item )">
    ## No header for pages.
</%def>

<%def name="render_item_links( page )">
</%def>

<%def name="render_item( page, page_data=None )">
    <div id="page-display-content" page_id="${page_data}">
    </div>
</%def>
