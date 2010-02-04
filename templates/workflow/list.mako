<%inherit file="/base.mako"/>

<%def name="title()">Workflow home</%def>

%if message:
<%
    try:
        messagetype
    except:
        messagetype = "done"
%>
<p />
<div class="${messagetype}message">
    ${message}
</div>
%endif

<h2>Your workflows</h2>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( action='create' )}">
            <img src="${h.url_for('/static/images/silk/add.png')}" />
            <span>Create new workflow</span>
        </a>
    </li>
</ul>
  
%if workflows:
    <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" style="width:100%;">
        <tr class="header">
            <th>Name</th>
            <th># of Steps</th>
            ## <th>Last Updated</th>
            <th></th>
        </tr>
        %for i, workflow in enumerate( workflows ):
            <tr>
                <td>
                    <div class="menubutton" style="float: left;" id="wf-${i}-popup">
                    ${workflow.name | h}
                    </div>
                </td>
                <td>${len(workflow.latest_workflow.steps)}</td>
                ## <td>${str(workflow.update_time)[:19]}</td>
                <td>
                    <div popupmenu="wf-${i}-popup">
                    <a class="action-button" href="${h.url_for( action='editor', id=trans.security.encode_id(workflow.id) )}" target="_parent">Edit</a>
                    <a class="action-button" href="${h.url_for( controller='root', action='index', workflow_id=trans.security.encode_id(workflow.id) )}" target="_parent">Run</a>
                    <a class="action-button" href="${h.url_for( action='sharing', id=trans.security.encode_id(workflow.id) )}">Share or Publish</a>
                    <a class="action-button" href="${h.url_for( action='clone', id=trans.security.encode_id(workflow.id) )}">Clone</a>
                    <a class="action-button" href="${h.url_for( action='rename', id=trans.security.encode_id(workflow.id) )}">Rename</a>
                    <a class="action-button" confirm="Are you sure you want to delete workflow '${workflow.name}'?" href="${h.url_for( action='delete', id=trans.security.encode_id(workflow.id) )}">Delete</a>
                    </div>
                </td>
            </tr>    
        %endfor
    </table>
%else:

    You have no workflows.

%endif

<h2>Workflows shared with you by others</h2>

%if shared_by_others:
    <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <th>Name</th>
            <th>Owner</th>
            <th># of Steps</th>
            <th></th>
        </tr>
        %for i, association in enumerate( shared_by_others ):
            <% workflow = association.stored_workflow %>
            <tr>
                <td>
                    <a class="menubutton" id="shared-${i}-popup" href="${h.url_for( action='run', id=trans.security.encode_id(workflow.id) )}">${workflow.name | h}</a>
                </td>
                <td>${workflow.user.email}</td>
                <td>${len(workflow.latest_workflow.steps)}</td>
                <td>
                    <div popupmenu="shared-${i}-popup">
						<a class="action-button" href="${h.url_for( action='display_by_username_and_slug', username=workflow.user.username, slug=workflow.slug)}" target="_top">View</a>
	                    <a class="action-button" href="${h.url_for( action='run', id=trans.security.encode_id(workflow.id) )}">Run</a>
	                    <a class="action-button" href="${h.url_for( action='clone', id=trans.security.encode_id(workflow.id) )}">Clone</a>
                    </div>
                </td>
            </tr>    
        %endfor
    </table>
%else:

    No workflows have been shared with you.

%endif

<h2>Other options</h2>

<a class="action-button" href="${h.url_for( action='configure_menu' )}">
    <span>Configure your workflow menu</span>
</a>