<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

%if message:
    ${render_msg( message, status )}
%endif
<script type="text/javascript">
var repositories = ${repositories};
var preview_repo_url = '${h.url_for(controller='admin_toolshed', action='preview_repository', tool_shed_url=tool_shed_url)}';
var repository_listing = {};
$(function() {
    console.log(repositories);
    require(["libs/jquery/jquery-ui"], function() {
        $( "#repository_search" ).autocomplete({
            source: repositories,
            select: function(event, ui) {
                window.location.href = preview_repo_url + '&tsr_id=' + ui.item.value;
            }
        });
    });
});
</script>
<style type="text/css">
.ui-autocomplete {
    width: 30%;
    border: 1px solid #000;
    background: #fff;
}
.ui-state-focus {
    background: #bbf;
}
</style>
<div class="grid-header"><h2>Repositories by Category</h2><ul class="manage-table-actions"></ul>
    <div id="standard-search" style="display: block;">
        <span class="ui-widget">
            <input class="search-box-input" id="repository_search" name="search" value="Search" size="39" type="text">
            <input class="search-box-input" id="repo_id" name="search" value="Search" size="39" type="hidden">
            <button class="submit-image" type="submit" title="Search" />
        </span>
    </div>
</div>
<table class="grid">
    <thead id="grid-table-header">
        <tr>
            <th id="Category.name-header"><a>Name</a><span class="sort-arrow"></span></th>
            <th id="Category.description-header"><a>Description</a><span class="sort-arrow"></span></th>
            <th id="null-header">Repositories<span class="sort-arrow"></span></th>
        </tr>
    </thead>
%for category in categories:
    <tr>
        <td>
            <a href="${h.url_for(controller='admin_toolshed', action='browse_tool_shed_category', category_id=category['id'], tool_shed_url=tool_shed_url)}">${category['name']}</a>
        </td>
        <td>${category['description']}</td>
        <td>${category['repositories']}</td>
    </tr>
%endfor
</table>
