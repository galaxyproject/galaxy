<%namespace file="/message.mako" import="render_msg" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/tool_shed/base_panels.mako'
       else:
           return '/base.mako'
%>

<%inherit file="${inherit(context)}"/>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" target="galaxy_main" href="${h.url_for( controller='repository', action='browse_categories' )}">Browse repositories</a></li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Repository capsule information</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Date and time exported:</label>
            ${export_info_dict.get( 'export_time', 'unknown' ) | h}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Exported from Tool Shed:</label>
            ${export_info_dict.get( 'tool_shed', 'unknown' ) | h}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Repository name:</label>
            ${export_info_dict.get( 'repository_name', 'unknown' ) | h}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Repository owner:</label>
            ${export_info_dict.get( 'repository_owner', 'unknown' ) | h}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Changeset revision:</label>
            ${export_info_dict.get( 'changeset_revision', 'unknown' ) | h}
        </div>
        <div style="clear: both"></div>
        <div class="form-row">
            <label>Repository dependencies included in capsule?:</label>
            ${export_info_dict.get( 'export_repository_dependencies', 'unknown' ) | h}
        </div>
        <div style="clear: both"></div>
    </div>
</div>

<div class="toolForm">
    <div class="toolFormTitle">Results of attempt to import ${len( import_results_tups )} repositories contained in the capsule</div>
    <div class="toolFormBody">
        <div class="form-row">
            <table class="grid">
                %for import_results_tup in import_results_tups:
                    <%
                        ok, name_owner_tup, results_message = import_results_tup
                        name, owner = name_owner_tup
                    %>
                    <tr><td>Archive of repository <b>${name}</b> owned by <b>${owner}</b><br/>${results_message}</td></tr>
                %endfor
            </table>
            <div style="clear: both"></div>
        </div>
    </div>
</div>
