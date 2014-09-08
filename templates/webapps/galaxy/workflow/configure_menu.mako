<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="workflow"
    self.message_box_visible=False
%>
</%def>

<%def name="title()">Configure workflow menu</%def>

<%def name="center_panel()">
    <div style="overflow: auto; height: 100%;">
        <div class="page-container" style="padding: 10px;">
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

<form action="${h.url_for(controller='workflow', action='configure_menu')}" method="POST">

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
                    ${util.unicodify( workflow.name )}
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
                    ${util.unicodify( workflow.name )}
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

%if not workflows and not shared_by_others:
        <tr>
            <td colspan="4">You do not have any accessible workflows.</td>
        </tr>
%endif

</table>

<p />
<input type="Submit" value="Save" />

</form>
        </div>
    </div>
</%def>
