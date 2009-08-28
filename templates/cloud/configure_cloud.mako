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
 
%if cloudCredentials:
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
            <th>Credentials name</th>
            <th>Default</th>
            <th></th>
        </tr>
        %for i, cloudCredential in enumerate( cloudCredentials ):
            <tr>
                <td>
                    ${cloudCredential.name}
                    <a id="cr-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                </td>
                ## Comment <td>${len(workflow.latest_workflow.steps)}</td>
                ##<td>${str(cloudCredential.update_time)[:19]}</td>
                <td>
                	##${str(cloudCredential.defaultCred)}
                	<%
						if cloudCredential.defaultCred:
							context.write('*')
					%>
				</td>
                
				<td>
                    <div popupmenu="cr-${i}-popup">
                    <a class="action-button" href="${h.url_for( action='view', id=trans.security.encode_id(cloudCredential.id) )}">View</a>
                    <a class="action-button" href="${h.url_for( action='rename', id=trans.security.encode_id(cloudCredential.id) )}">Rename</a>
                    <a class="action-button" href="${h.url_for( action='makeDefault', id=trans.security.encode_id(cloudCredential.id) )}" target="_parent">Make default</a>
                    <a class="action-button" confirm="Are you sure you want to delete credentials '${cloudCredential.name}'?" href="${h.url_for( action='delete', id=trans.security.encode_id(cloudCredential.id) )}">Delete</a>
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
        <colgroup width="40%"></colgroup>
		<colgroup width="15%"></colgroup>
		<colgroup width="10%"></colgroup>
		<colgroup width="35%"></colgroup>
		<tr class="header">
            <th>Live instances</th>
			<th>Storage size (GB)</th>
			<th>State</th>
            <th>Alive since</th>
			<th></th>
        </tr>
		%if liveInstances:
	        %for i, liveInstance in enumerate( liveInstances ):
	            <tr>
	                <td>
	                	${liveInstance.name}
	                    <a id="li-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
	                </td>
					<td>${str(liveInstance.total_size)}</td> <!--TODO:Replace with vol size once available-->
	                <td>${str(liveInstance.state)}</td>
	                <td>
	                	${str(liveInstance.launch_time)[:16]} 
	                	<%
							from datetime import datetime
							from datetime import timedelta
	
							# DB stores all times in GMT, so adjust for difference (4 hours)
							adjustedStarttime = liveInstance.update_time - timedelta(hours=4)
	
							# (NOT CURRENTLY USED BLOCK OF CODE) Calculate time difference from now
							delta = datetime.now() - adjustedStarttime
							#context.write( str(datetime.utcnow() ) )
							#context.write( str(delta) )
							
							# This is where current time and since duration is calculated
							#context.write( str( liveInstance.launch_time ) )
							context.write( ' UTC (' )
							context.write( str(h.date.distance_of_time_in_words (liveInstance.launch_time, h.date.datetime.utcnow() ) ) )
							
							
						%>)
					</td>
	                <td>
	                    <div popupmenu="li-${i}-popup">
	                    <a class="action-button" confirm="Are you sure you want to stop instance '${liveInstance.name}'?" href="${h.url_for( action='stop', id=trans.security.encode_id(liveInstance.id) )}">Stop</a>
	                    <a class="action-button" href="${h.url_for( action='renameInstance', id=trans.security.encode_id(liveInstance.id) )}">Rename</a>
	                    <a class="action-button" href="${h.url_for( action='viewInstance', id=trans.security.encode_id(liveInstance.id) )}">View details</a>
	                    </div>
	                </td>
	            </tr>    
	        %endfor
		%else:
			<tr>
				<td>Currently, you have no live instances.</td>
			</tr>
		%endif
    </table>
	
	## *****************************************************
	## Manage previously configured instances
	<table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <colgroup width="40%"></colgroup>
		<colgroup width="15%"></colgroup>
		<colgroup width="10%"></colgroup>
		<colgroup width="35%"></colgroup>
		<tr class="header">
            <th>Previously configured instances</th>
            ##<th>Storage size (GB)</th>
			##<th>State</th>
            ##<th>Alive since</th>
			<th></th>
			<th></th>
			<th></th>
			<th></th>
        </tr>
        
		%if prevInstances:
			%for i, prevInstance in enumerate( prevInstances ):
	            <tr>
	                <td>
	                    ${prevInstance.name}
	                    <a id="pi-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
	                </td>
	                <td>${str(prevInstance.total_size)}</td> <!-- TODO: Change to show vol size once available--> 
	                <td>${str(prevInstance.state)}</td>
					<td>N/A</td>
	                <td>
	                    <div popupmenu="pi-${i}-popup">
	                    <a class="action-button" href="${h.url_for( action='start', id=trans.security.encode_id(prevInstance.id) )}">Start</a>
	                    <a class="action-button" href="${h.url_for( action='renameInstance', id=trans.security.encode_id(prevInstance.id) )}">Rename</a>
	                    <a class="action-button" href="${h.url_for( action='addStorage', id=trans.security.encode_id(prevInstance.id) )}" target="_parent">Add storage</a>
	                    <a class="action-button" confirm="Are you sure you want to delete instance '${prevInstance.name}'? This will delete all of your data assocaiated with this instance!" href="${h.url_for( action='deleteInstance', id=trans.security.encode_id(prevInstance.id) )}">Delete</a>
	                    </div>
	                </td>
	            </tr>    
	        %endfor
		%else:
			<tr>
				<td>You have no previously configured instances (or they are all currently alive).</td>
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