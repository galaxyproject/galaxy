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
        <a class="action-button" href="${h.url_for( controller="workflow", action='index' )}" target="_parent">
            <span>Switch to workflow management view</span>
        </a>
    </li>
</ul>
  
%if workflows:
    <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <th>Name</th>
            <th># of Steps</th>
            ## <th>Last Updated</th>
            <th></th>
        </tr>
        %for i, workflow in enumerate( workflows ):
            <tr>
                <td>
                    <a href="${h.url_for( action='run', id=trans.security.encode_id(workflow.id) )}">${h.to_unicode( workflow.name )}</a>
                    <a id="wf-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                </td>
                <td>${len(workflow.latest_workflow.steps)}</td>
                ## <td>${str(workflow.update_time)[:19]}</td>
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
            </tr>    
        %endfor
    </table>
%else:

    No workflows have been shared with you.

%endif