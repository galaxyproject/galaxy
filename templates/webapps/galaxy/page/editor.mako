<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="user"
    self.overlay_visible=False
%>
</%def>

<%def name="javascript_app()">
    ${parent.javascript_app()}
    <script type="text/javascript">
        // Define global variables needed by galaxy.pages script.
        // Apparently pages() relies on these variables being defined
        // in window. 
        config.addInitialization(function(){
            var pagesConfig = {
                page_id: "${trans.security.encode_id(page.id)}",
                page_list_url: '${h.url_for( controller='pages', action='list' )}',
                list_objects_url: "${h.url_for(controller='page', action='LIST_ACTION' )}",
                set_accessible_url: "${h.url_for( controller='ITEM_CONTROLLER', action='set_accessible_async' )}",
                get_name_and_link_url: "${h.url_for( controller='ITEM_CONTROLLER', action='get_name_and_link_async' )}?id=",
                editor_base_path: "${h.url_for('/static/wymeditor')}/",
                iframe_base_path: "${h.url_for('/static/wymeditor/iframe/galaxy')}/",
                save_url: "${h.url_for(controller='page', action='save' )}"
            };
            console.log("editor.mako, javascript_app", "define variables needed by galaxy.pages script");
            window.bundleEntries.pages(pagesConfig);
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "base", "embed_item" )}
    <style type='text/css'>
        .galaxy-page-editor-button
        {
            position: relative;
            float: left;
            padding: 0.2em;
        }
    </style>
</%def>

<%def name="center_panel()">

    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            Page Editor: ${page.title | h}
            <a id="save-button" class="btn btn-secondary fa fa-save float-right"></a>
        </div>
    </div>

    <div class="unified-panel-body">
        <textarea name="page_content">${ content }</textarea>
    </div>

</%def>
