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
    <h2>Repositories in ${category['name']}</h2>
    <table class="grid">
        <thead id="grid-table-header">
            <tr>
                <th style="width: 10%;">Owner</th>
                <th style="width: 15%;">Name</th>
                <th>Synopsis</th>
                <th style="width: 10%;">Type</th>
                <th style="width: 5%;">Certified</th>
            </tr>
        </thead>
    %for repository in category['repositories']:
        <tr>
            <td>${repository['owner']}</td>
            <td>
                <a href="${h.url_for( controller='admin_toolshed', action='preview_repository', tool_shed_url=tool_shed_url, tsr_id=repository['id'] )}">${repository['name']}</a>
            </td>
            <td>${repository['description']}</td>
            <td>${repository['type']}</td>
            %if 'tools_functionally_correct' in repository['metadata'] and repository['metadata']['tools_functionally_correct']:
                <td>Yes</td>
            %else:
                <td>No</td>
            %endif
        </tr>
    %endfor
    </table>
<div>
