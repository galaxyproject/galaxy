<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
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
$(function() {
    require(["libs/jquery/jquery-ui"], function() {
        $( "#repository_search" ).autocomplete({
            source: repositories,
            select: function(event, ui) {
                window.location.href = preview_repo_url + '&tsr_id=' + ui.item.value;
            },
            focus: function( event, ui ) {
                event.preventDefault();
                $(this).val(ui.item.label);
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
<div id="standard-search" style="height: 2em; margin: 1em;">
    <span class="ui-widget" >
        <input class="search-box-input" id="repository_search" name="search" placeholder="Search repositories by name or id" size="60" type="text" />
    </span>
</div>

<div style="clear: both; margin-top: 1em;">
    <h2>Repositories by Category</h2>
    <table class="grid">
        <thead id="grid-table-header">
            <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Repositories</th>
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
</div>
