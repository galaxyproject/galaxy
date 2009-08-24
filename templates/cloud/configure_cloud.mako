<%inherit file="/base.mako"/>

<%def name="title()">Cloud home</%def>

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
	<ul class="manage-table-actions">
	    <li>
	        <a class="action-button" href="${h.url_for( action='add' )}">
	            <img src="${h.url_for('/static/images/silk/add.png')}" />
	            <span>Add AWS credentials</span>
	        </a>
	    </li>
	</ul>

    <table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <th>Credentials Name</th>
            <th>Default</th>
            ## <th>Last Updated</th>
            <th></th>
        </tr>
        %for i, awsCredential in enumerate( awsCredentials ):
            <tr>
                <td>
                    ${awsCredential.name}
                    <a id="wf-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                </td>
                ## Comment <td>${len(workflow.latest_workflow.steps)}</td>
                ##<td>${str(awsCredentials.update_time)[:19]}</td>
                <td>
                    <div popupmenu="wf-${i}-popup">
                    <a class="action-button" href="${h.url_for( action='view', id=trans.security.encode_id(awsCredential.id) )}">View</a>
                    <a class="action-button" href="${h.url_for( action='rename', id=trans.security.encode_id(awsCredential.id) )}">Rename</a>
                    <a class="action-button" href="${h.url_for( action='makeDefault', id=trans.security.encode_id(awsCredential.id) )}" target="_parent">Make default</a>
                    <a class="action-button" confirm="Are you sure you want to delete workflow '${awsCredential.name}'?" href="${h.url_for( action='delete', id=trans.security.encode_id(awsCredential.id) )}">Delete</a>
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

