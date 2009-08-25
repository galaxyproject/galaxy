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
	## Manage user credentials
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
            <th></th>
        </tr>
        %for i, awsCredential in enumerate( awsCredentials ):
            <tr>
                <td>
                    ${awsCredential.name}
                    <a id="wf-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                </td>
                ## Comment <td>${len(workflow.latest_workflow.steps)}</td>
                ##<td>${str(awsCredential.update_time)[:19]}</td>
                <td>
                	##${str(awsCredential.defaultCred)}
                	<%
						if awsCredential.defaultCred:
							context.write('*')
					%>
				</td>
                
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
	
	## *****************************************************
	## Manage live instances
	<p />
	<h2>Manage cloud instances</h2>
	<ul class="manage-table-actions">
	    <li>
	        <a class="action-button" href="${h.url_for( action='configureNew' )}">
	            <img src="${h.url_for('/static/images/silk/add.png')}" />
	            <span>Configure new instance</span>
	        </a>
	    </li>
	</ul>

    <table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <th>Live instances</th>
            <th>Alive since</th>
            <th></th>
        </tr>
        %for i, awsCredential in enumerate( awsCredentials ):
            <tr>
                <td>
                    ${awsCredential.name}
                    <a id="wf-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                </td>
                <td>
                	##${str(awsCredential.update_time)[:19]} 
                	<%
						from datetime import datetime
						from datetime import timedelta

						# DB stores all times in GMT, so adjust for difference (4 hours)
						adjustedStarttime = awsCredential.update_time - timedelta(hours=4)

						# (NOT CURRENTLY USED BLOCK OF CODE) Calculate time difference from now
						delta = datetime.now() - adjustedStarttime
						#context.write( str(datetime.utcnow() ) )
						#context.write( str(delta) )
						
						# This is where current time and since duration is calculated
						context.write( str( awsCredential.update_time ) )
						context.write( ' UTC (' )
						context.write( str(h.date.distance_of_time_in_words (awsCredential.update_time, h.date.datetime.utcnow() ) ) )
					%>)
				</td>
                
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
	
	## *****************************************************
	## Manage previously configured instances
	<p /> <p />
	<table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <th>Previously configured instances</th>
            <th>Action</th>
            <th></th>
        </tr>
        
		%if prevInstances:
			%for i, prevInstance in enumerate( prevInstances ):
	            <tr>
	                <td>
	                    ${prevInstance.name}
	                    <a id="wf-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
	                </td>
	                ## Comment <td>${len(workflow.latest_workflow.steps)}</td>
	                ##<td>${str(awsCredential.update_time)[:19]}</td>
	                <td>
	                	<a class="action-button" href="${h.url_for( action='start', id=trans.security.encode_id(awsCredential.id) )}">Start</a>
	               </td>
	                
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
		%else:
			<tr>
				<td>You have no previously configured instances.</td>
			</tr>
		%endif
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

<p /><br />
<ul class="manage-table-actions">
	<li>
		<a class="action-button" href="${h.url_for( action='addNewImage' )}"><span>Add new image</span></a>
	</li>
</ul>