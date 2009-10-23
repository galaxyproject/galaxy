<%inherit file="/base.mako"/>

<%def name="title()">Cloud home</%def>

%if message:
<%
    try:
        messagetype
    except:
        messagetype = "done"
%>

<div class="${messagetype}message">
    ${message}
</div>
%endif

<%def name="javascripts()">
${parent.javascripts()}
${h.js( "jquery" )}

<script type="text/javascript">
	function update_state() {
		$.getJSON( "${h.url_for( action='json_update' )}", {}, function ( data ) {
			for (var i in data) {
			var elem = '#' + data[i].id;
				$(elem + "-state").text( data[i].state );
				if (data[i].launch_time) {
					$(elem + "-launch_time").text( data[i].launch_time.substring(0, 16 ) + " (" + data[i].time_ago + ")" );
				}
				else {
					$(elem + "-launch_time").text( "N/A" );
				}
			}
		});
		setTimeout("update_state()", 10000);
	}
	
	$(function() {
		update_state();
	});
</script>
</%def>

<h2>Galaxy in the clouds</h2>
 
%if cloudCredentials:
	## Manage user credentials
	<ul class="manage-table-actions">
	    <li>
	        <a class="action-button" href="${h.url_for( action='add' )}">
	            <img src="${h.url_for('/static/images/silk/add.png')}" />
	            <span>Add credentials</span>
	        </a>
	    </li>
	</ul>

    <table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <th>Credentials name</th>
            <th>Provider name (type)</th>
            <th></th>
        </tr>
        %for i, cloudCredential in enumerate( cloudCredentials ):
            <tr>
                <td>
                    ${cloudCredential.name}
					<a id="cr-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                </td>
                <td>
                	${cloudCredential.provider.name}
					(${cloudCredential.provider.type})
				</td>
				<td>
                    <div popupmenu="cr-${i}-popup">
                    <a class="action-button" href="${h.url_for( action='view', id=trans.security.encode_id(cloudCredential.id) )}">View</a>
					<a class="action-button" href="${h.url_for( action='rename', id=trans.security.encode_id(cloudCredential.id) )}">Rename</a>
                    <a class="action-button" confirm="Are you sure you want to delete credentials '${cloudCredential.name}'?" href="${h.url_for( action='delete', id=trans.security.encode_id(cloudCredential.id) )}">Delete</a>
                    </div>
                </td>
            </tr>    
        %endfor
    </table>
	
	## *****************************************************
	## Manage live instances
	<p />
	<h2>Manage your cloud instances</h2>
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
		<colgroup width="25%"></colgroup>
		<colgroup width="10%"></colgroup>
		<tr class="header">
            <th>Instance name (credentials)</th>
			<th>Storage size (GB)</th>
			<th>State</th>
            <th>Alive since</th>
            <th></th>
			<th></th>
        </tr>
		%if liveInstances:
	        %for i, liveInstance in enumerate( liveInstances ):
	            <tr>
	                <td>
	                	${liveInstance.name} (${liveInstance.credentials.name})
	                    <a id="li-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
	                </td>
					<td>${str(liveInstance.total_size)}</td>
	                <td id="${ liveInstance.id }-state">${str(liveInstance.state)}</td>
	                <td id="${ liveInstance.id }-launch_time">
	                	##${str(liveInstance.launch_time)[:16]} 
	                	<%
							#from datetime import datetime
							#from datetime import timedelta
	
							# DB stores all times in GMT, so adjust for difference (4 hours)
							#adjustedStarttime = liveInstance.update_time - timedelta(hours=4)
	
							#delta = datetime.now() - adjustedStarttime
							#context.write( str(datetime.utcnow() ) )
							#context.write( str(delta) )
							
							# This is where current time and since duration is calculated
							if liveInstance.launch_time is None:
								context.write( 'N/A' )
							else:
								context.write( str( liveInstance.launch_time )[:16] )
								context.write( ' UTC (' )
								context.write( str(h.date.distance_of_time_in_words (liveInstance.launch_time, h.date.datetime.utcnow() ) ) )
								context.write( ')' )
						%>
					</td>
					<td><div align="right">
						%for j, instance in enumerate( liveInstance.instance ):
						## TODO: Once more instances will be running under the same liveInstance, additional logic will need to be added to account for that
							%if instance.state == "running":
								## Wait until Galaxy server starts to show 'Access Galaxy' button
								<%
								import urllib2
								try:
									urllib2.urlopen("http://"+instance.public_dns)
									context.write( '<a class="action-button" href="http://'+instance.public_dns+'" target="_blank">' )
									context.write( '<span>Access Galaxy</span>' )
									context.write( '<img src="'+h.url_for('/static/images/silk/resultset_next.png')+'" /></a></div>' )
								except urllib2.URLError:
									context.write( '<span>Galaxy starting...</span>' )
								%>
								
							%endif
						%endfor
	            	</td>
	                <td>
	                    <div popupmenu="li-${i}-popup">
	                    <a class="action-button" confirm="Are you sure you want to stop instance '${liveInstance.name}'? Please note that this may take up to 1 minute during which time the page will not refresh." href="${h.url_for( action='stop', id=trans.security.encode_id(liveInstance.id) )}">Stop</a>
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
	<table class="mange-table noHR" border="0" cellspacing="0" cellpadding="0" width="100%">
        <colgroup width="40%"></colgroup>
		<colgroup width="15%"></colgroup>
		<colgroup width="10%"></colgroup>
		<colgroup width="35%"></colgroup>
		##<tr class="header">
            ##<th>Previously configured instances</th>
            ##<th>Storage size (GB)</th>
			##<th>State</th>
            ##<th>Alive since</th>
			##<th></th>
			##<th></th>
			##<th></th>
			##<th></th>
        ##</tr>
        
		%if prevInstances:
			%for i, prevInstance in enumerate( prevInstances ):
	            <tr>
	                <td>
	                    ${prevInstance.name} (${prevInstance.credentials.name})
	                    <a id="pi-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
	                </td>
	                <td>${str(prevInstance.total_size)}</td> <!-- TODO: Change to show vol size once available--> 
	                <td>
	                	<%state = str(prevInstance.state)%> 
	                	%if state =='error':
							<div id="short">
			                   <a onclick="document.getElementById('full').style.display = 'block'; 
			                    document.getElementById('short').style.display = 'none'; return 0" 
			                    href="javascript:void(0)">
			                    error
			                   </a>                    
			                </div>
			                <div id="full" style="DISPLAY: none">
					      		<a onclick="document.getElementById('short').style.display = 'block'; 
			                    document.getElementById('full').style.display = 'none'; return 0;" 
			                    href="javascript:void(0)">
			                    ${str(prevInstance.error)}
			                    </a>            
			               </div>
						%else:
							${str(prevInstance.state)}
						%endif
					</td>
					<td>N/A</td>
	                <td>
	                    <div popupmenu="pi-${i}-popup">
	                    <a class="action-button" href="${h.url_for( action='start', id=trans.security.encode_id(prevInstance.id), type='m1.small' )}"> Start m1.small</a>
	                    <a class="action-button" href="${h.url_for( action='start', id=trans.security.encode_id(prevInstance.id), type='c1.medium' )}"> Start c1.medium</a>
						<a class="action-button" href="${h.url_for( action='renameInstance', id=trans.security.encode_id(prevInstance.id) )}">Rename</a>
	                    <a class="action-button" href="${h.url_for( action='addStorage', id=trans.security.encode_id(prevInstance.id) )}" target="_parent">Add storage</a>
						<a class="action-button" href="${h.url_for( action='usageReport' )}">Usage report</a>
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