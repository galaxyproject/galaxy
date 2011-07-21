<%inherit file="/base.mako"/>

<%def name="title()">Configure workflow menu</%def>

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

<form action="${h.url_for()}" method="POST">

<table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
    <tr class="header">
        <th>Name</th>
        <th>Owner</th>
        <th># of Steps</th>
        ## <th>Last Updated</th>
        <th>Show in menu</th>
    </tr>
        
%if workflows:

        %for i, workflow in enumerate( workflows ):
            <tr>
                <td>
                    ${workflow.name}
                </td>
                <td>You</td>
                <td>${len(workflow.latest_workflow.steps)}</td>
                <td>
                    <input type="checkbox" name="workflow_ids" value="${workflow.id}"
                    %if workflow.id in ids_in_menu:
                        checked
                    %endif
                    />
                </td>
            </tr>    
        %endfor

%endif

%if shared_by_others:

        %for i, association in enumerate( shared_by_others ):
            <% workflow = association.stored_workflow %>
            <tr>
                <td>
                    ${workflow.name}
                </td>
                <td>${workflow.user.email}</td>
                <td>${len(workflow.latest_workflow.steps)}</td>
                <td>
                    <input type="checkbox" name="workflow_ids" value="${workflow.id}"
                    %if workflow.id in ids_in_menu:
                        checked
                    %endif
                    />
                </td>
            </tr>    
        %endfor

%endif

</table>

<p />
<input type="Submit" />

</form>