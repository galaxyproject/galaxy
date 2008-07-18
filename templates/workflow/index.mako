<%inherit file="/base.mako"/>

<%def name="title()">Workflow home</%def>

<div class="warningmessage">
    Workflow support is currently in <b><i>beta</i></b> testing.
    Workflows may not work with all tools, may fail unexpectedly, and may
    not be compatible with future updates to <b>Galaxy</b>.
</div>

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

<div>
    <div style="float: right;">
        <a class="action-button" href="${h.url_for( action='create' )}">
            <img src="${h.url_for('/static/images/silk/add.png')}" />
            <span>Add a new workflow</span>
        </a>
    </div>
    <h2>Your workflows</h2>
</div>

%if workflows:
    <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <th>Name</th>
            <th># of Steps</th>
            ## <th>Last Updated</th>
            <th></th>
        </tr>
        %for i, workflow in enumerate( workflows ):
            <tr>
                <td>
                    <a href="${h.url_for( action='run', id=trans.security.encode_id(workflow.id) )}">${workflow.name}</a>
                    <a id="wf-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                </td>
                <td>${len(workflow.latest_workflow.steps)}</td>
                ## <td>${str(workflow.update_time)[:19]}</td>
                <td>
                    <div popupmenu="wf-${i}-popup">
                    <a class="action-button" href="${h.url_for( action='run', id=trans.security.encode_id(workflow.id) )}">Run</a>
                    <a class="action-button" href="${h.url_for( action='editor', id=trans.security.encode_id(workflow.id) )}" target="_parent">Edit</a>
                    <a class="action-button" href="${h.url_for( action='rename', id=trans.security.encode_id(workflow.id) )}">Rename</a>
                    <a class="action-button" href="${h.url_for( action='share', id=trans.security.encode_id(workflow.id) )}">Share</a>
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
                    <a href="${h.url_for( action='run', id=trans.security.encode_id(workflow.id) )}">${workflow.name}</a>
                    <a id="shared-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                </td>
                <td>${workflow.user.email}</td>
                <td>${len(workflow.latest_workflow.steps)}</td>
                <td>
                    <div popupmenu="shared-${i}-popup">
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