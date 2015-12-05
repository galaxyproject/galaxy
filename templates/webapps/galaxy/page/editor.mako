<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="user"
    self.overlay_visible=False
%>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        // Define variables needed by galaxy.pages script.
        var page_id = "${trans.security.encode_id(page.id)}",
            page_list_url = '${h.url_for( controller='page', action='list' )}',
            list_objects_url = "${h.url_for(controller='page', action='LIST_ACTION' )}",
            set_accessible_url = "${h.url_for( controller='ITEM_CONTROLLER', action='set_accessible_async' )}",
            get_name_and_link_url = "${h.url_for( controller='ITEM_CONTROLLER', action='get_name_and_link_async' )}?id=",
            list_histories_for_selection_url = "${h.url_for(controller='page', action='list_histories_for_selection' )}",
            editor_base_path = "${h.url_for('/static/wymeditor')}/",
            iframe_base_path = "${h.url_for('/static/wymeditor/iframe/galaxy')}/",
            save_url = "${h.url_for(controller='page', action='save' )}";
    </script>
    ${h.js(
        "libs/jquery/jquery.form",
        "libs/jquery/jstorage",
        "libs/jquery/jquery.wymeditor",
        "libs/jquery/jquery.autocomplete",
        "galaxy.pages"
    )}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "base", "autocomplete_tagging", "embed_item" )}
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
        <div class="unified-panel-header-inner" style="float: right">
            <a id="save-button" class="panel-header-button">Save</a>
            <a id="close-button" class="panel-header-button">Close</a>
        </div>
        <div class="unified-panel-header-inner">
            Page Editor <span style="font-weight: normal">| Title : ${page.title | h}</span>
        </div>
    </div>

    <div class="unified-panel-body">
        <textarea name="page_content">${util.unicodify( page.latest_revision.content )}</textarea>
    </div>

</%def>
