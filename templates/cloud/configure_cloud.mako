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

<h2>Galaxy in the clouds</h2>
 
%if awsCredentials:
    <table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <th>Name</th>
            <th># of Steps</th>
            ## <th>Last Updated</th>
            <th></th>
        </tr>
        %for i, workflow in enumerate( workflows ):
            <tr>
                <td>
                    ${workflow.name}
                    <a id="wf-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                </td>
                <td>${len(workflow.latest_workflow.steps)}</td>
                ## <td>${str(workflow.update_time)[:19]}</td>
                <td>
                    <div popupmenu="wf-${i}-popup">
                    <a class="action-button" href="${h.url_for( action='editor', id=trans.security.encode_id(workflow.id) )}" target="_parent">Edit</a>
                    <a class="action-button" href="${h.url_for( controller='root', action='index', workflow_id=trans.security.encode_id(workflow.id) )}" target="_parent">Run</a>
                    <a class="action-button" href="${h.url_for( action='clone', id=trans.security.encode_id(workflow.id) )}">Clone</a>
                    <a class="action-button" href="${h.url_for( action='rename', id=trans.security.encode_id(workflow.id) )}">Rename</a>
                    <a class="action-button" href="${h.url_for( action='sharing', id=trans.security.encode_id(workflow.id) )}">Sharing</a>
                    <a class="action-button" confirm="Are you sure you want to delete workflow '${workflow.name}'?" href="${h.url_for( action='delete', id=trans.security.encode_id(workflow.id) )}">Delete</a>
                    </div>
                </td>
            </tr>    
        %endfor
    </table>
%else:

    You have no AWS credentials associated with your Galaxy account: 
	<a class="action-button" href="${h.url_for( action='add' )}">
        <img src="${h.url_for('/static/images/silk/add.png')}" />
        <span>Add AWS credentials</span>
    </a>
	 or 
	<a href="http://aws.amazon.com/" target="_blank">
        open AWS account with Amazon</a>.
	
%endif

