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
				// Because of different list managing 'live' vs. 'available' instances, reload url on various state changes
				old_state = $(elem + "-state").text();
				prev_old_state = $(elem + "-state-p").text();
				new_state = data[i].state;
				console.log( "old_state[%d] = %s", i, old_state );
				console.log( "prev_old_state[%d] = %s", i, prev_old_state );
				console.log( "new_state[%d] = %s", i, new_state );
				if ( ( old_state=='pending' && new_state=='running' ) ||  ( old_state=='shutting-down' && new_state=='available' ) || \
					 ( old_state=='running' && new_state=='available' ) || ( old_state=='running' && new_state=='error' ) || \
					 ( old_state=='pending' && new_state=='error' ) || ( old_state=='pending' && new_state=='available' ) || \
					 ( old_state=='submitted' && new_state=='available' ) || ( prev_old_state.match('newUCI') && new_state=='available' ) || \
					 ( prev_old_state.match('new') && new_state=='available' ) || ( prev_old_state.match('deletingUCI') && new_state=='deleted' ) || \
					 ( prev_old_state.match('deleting') && new_state=='deleted' ) ) {
					var url = "${h.url_for( controller='cloud', action='list')}";
					location.replace( url );
				}
				else if ( ( old_state=='running' && new_state=='error' ) || ( old_state=='pending' && new_state=='error' ) || \
					( old_state=='submitted' && new_state=='error' ) || ( old_state=='submittedUCI' && new_state=='error' ) || \
					( old_state=='shutting-down' && new_state=='error' ) || ( prev_old_state.match('newUCI') && new_state=='error' ) || \
					( prev_old_state.match('new') && new_state=='error' ) || \
					( prev_old_state.match('deleting') && new_state=='error' ) || ( prev_old_state.match('deletingUCI') && new_state=='error' ) ) {
					// TODO: Following clause causes constant page refresh for an exception thrown as a result of instance not starting correctly - need alternative method!
					//( prev_old_state.match('available') && new_state=='error' ) || \
					
					var url = "${h.url_for( controller='cloud', action='list')}";
					location.replace( url );
				} 
				
				if ( new_state=='shutting-down' || new_state=='shutting-downUCI' ) {
					$(elem + "-link").text( "" );
				}
				
				// Check if Galaxy website is accessible on given instance; if so, provide link. Otherwise, wait more.
				else if ( ( $(elem+"-link").text().match('starting') || $(elem+"-link").text()=='' ) && new_state=='running' ) {
					//console.log ( 'elem.text: ' + $(elem+"-link").text() );
					$.getJSON( "${h.url_for( action='link_update' )}", { uci_id: data[i].id }, function ( data ) {
						for (var i in data) {
							var dns = data[i].public_dns;
							var uci = '#' + data[i].uci_id;
							if( !dns ) {
								$(uci+"-link").text( 'Galaxy starting...' );
								// http://stackoverflow.com/questions/275931/how-do-you-make-an-element-flash-in-jquery
								//$(uci+"-link").stop().animate({ fontSize: "14px" }, 1000).animate({ fontSize: "12px" }, 1000);
							}
							else {
								$(uci+"-link").html( '<div align="right"><a class="action-button" href="http://'+dns+'" target="_blank">' + 
									'<span>Access Galaxy</span>'+
									'<img src="' + "${h.url_for( '/static/images/silk/resultset_next.png' )}" + '" /></div>' );
								//$(uci+"-link").stop().animate({ fontSize: "14px" }, 1000).animate({ fontSize: "12px" }, 1000);
							}
						}
					});
				}
				
				// Update 'state' and 'time alive' fields
				$(elem + "-state").text( data[i].state );
				if (data[i].launch_time) {
					$(elem + "-launch_time").text( data[i].launch_time.substring(0, 16 ) + " UTC (" + data[i].time_ago + ")" );
				}
				else {
					$(elem + "-launch_time").text( "N/A" );
				}
			}
		});
		setTimeout("update_state()", 15000);
	}
	
	$(function() {
		update_state();
	});
	
</script>
</%def>

<h2>Galaxy in the clouds</h2>

%if cloudProviders:
	## Manage user-registered cloud providers
	<h3>Your registered cloud providers</h3>
	<ul class="manage-table-actions">
	    <li>
	        <a class="action-button" href="${h.url_for( action='add_provider' )}">
	            <img src="${h.url_for('/static/images/silk/add.png')}" />
	            <span>Add provider</span>
	        </a>
	    </li>
	</ul>

    <table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <th>Provider name</th>
            <th>Provider type</th>
            <th></th>
        </tr>
        %for i, cloudProvder in enumerate( cloudProviders ):
            <tr>
                <td>
                    ${cloudProvder.name}
					<a id="cp-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                </td>
                <td>
                	${cloudProvder.type}
				</td>
				<td>
                    <div popupmenu="cp-${i}-popup">
                    <a class="action-button" href="${h.url_for( action='view_provider', id=trans.security.encode_id(cloudProvder.id) )}">View</a>
					<a class="action-button" href="${h.url_for( action='edit_provider', id=trans.security.encode_id(cloudProvder.id) )}">Edit</a>
                    <a class="action-button" confirm="Are you sure you want to delete cloud provider '${cloudProvder.name}'?" href="${h.url_for( action='delete_provider', id=trans.security.encode_id(cloudProvder.id) )}">Delete</a>
                    </div>
                </td>
            </tr>    
        %endfor
    </table>
	

	## *****************************************************
	## Manage user credentials
	<h3>Your registered cloud credentials</h3>
	
	%if cloudCredentials:
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
						<a class="action-button" href="${h.url_for( action='edit', id=trans.security.encode_id(cloudCredential.id) )}">Edit</a>
	                    <a class="action-button" confirm="Are you sure you want to delete credentials '${cloudCredential.name}'?" href="${h.url_for( action='delete', id=trans.security.encode_id(cloudCredential.id) )}">Delete</a>
	                    </div>
	                </td>
	            </tr>    
	        %endfor
	    </table>
		
		## *****************************************************
		## Manage live instances
		<p />
		<h3>Manage your cloud instances</h3>
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
	            <th>Live instance name (credentials)</th>
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
						## Handled by JavaScript function
						<td id="${ liveInstance.id }-link"></td> 
		                <td>
		                    <div popupmenu="li-${i}-popup">
		                    <a class="action-button" confirm="Are you sure you want to stop instance '${liveInstance.name}'? Please note that this may take up to 1 minute during which time the page will not refresh." href="${h.url_for( action='stop', id=trans.security.encode_id(liveInstance.id) )}">Stop</a>
		                    <a class="action-button" href="${h.url_for( action='renameInstance', id=trans.security.encode_id(liveInstance.id) )}">Rename</a>
		                    <a class="action-button" href="${h.url_for( action='viewInstance', id=trans.security.encode_id(liveInstance.id) )}">View details</a>
		                    <a class="action-button" href="${h.url_for( action='usageReport', id=trans.security.encode_id(liveInstance.id) )}">Usage report</a>
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
		<p />
		## *****************************************************
		## Manage previously configured instances
		## <table class="mange-table noHR" border="0" cellspacing="0" cellpadding="0" width="100%">
		<table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
	        <colgroup width="40%"></colgroup>
			<colgroup width="15%"></colgroup>
			<colgroup width="10%"></colgroup>
			<colgroup width="25%"></colgroup>
			<colgroup width="10%"></colgroup>
			<tr class="header">
	            <th>Configured instance name (credentials)</th>
				<th>Storage size (GB)</th>
				<th>State</th>
	            <th></th>
				<th></th>
	        </tr>
	        
			%if prevInstances:
				%for i, prevInstance in enumerate( prevInstances ):
		            <tr>
		                <td>
		                    ${prevInstance.name} (${prevInstance.credentials.name})
		                    <a id="pi-${i}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
		                </td>
		                <td>${str(prevInstance.total_size)}</td> 
		                <td id="${ prevInstance.id }-state-p">
		                	<%state = str(prevInstance.state)%> 
		                	%if state =='error':
								<div id="${prevInstance.name}-short">
				                   <a onclick="document.getElementById('${prevInstance.name}-full').style.display = 'block'; 
								    document.getElementById('${prevInstance.name}-short').style.display = 'none'; return 0" 
				                    href="javascript:void(0)">
				                    error
				                   </a>                    
				                </div>
				                <div id="${prevInstance.name}-full" style="DISPLAY: none">
						      		<a onclick="document.getElementById('${prevInstance.name}-short').style.display = 'block'; 
									document.getElementById('${prevInstance.name}-full').style.display = 'none'; return 0;" 
				                    href="javascript:void(0)">
				                    error:</a><br />
									${str(prevInstance.error)}
									<p />
									<div style="font-size:10px;">
									<a href="${h.url_for( action='set_uci_state', id=trans.security.encode_id(prevInstance.id), state='available' )}">reset state</a>
									</div>
				               </div>
							%else:
								${str(prevInstance.state)}
							%endif
						</td>
						<td>
		                    <div popupmenu="pi-${i}-popup">
		                    <a class="action-button" href="${h.url_for( action='start', id=trans.security.encode_id(prevInstance.id), type='m1.small' )}"> Start m1.small</a>
		                    <a class="action-button" href="${h.url_for( action='start', id=trans.security.encode_id(prevInstance.id), type='c1.medium' )}"> Start c1.medium</a>
							<a class="action-button" href="${h.url_for( action='renameInstance', id=trans.security.encode_id(prevInstance.id) )}">Rename</a>
		                    <a class="action-button" href="${h.url_for( action='addStorage', id=trans.security.encode_id(prevInstance.id) )}" target="_parent">Add storage</a>
							<a class="action-button" href="${h.url_for( action='usageReport', id=trans.security.encode_id(prevInstance.id) )}">Usage report</a>
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
	   You have no credentials associated with your Galaxy account: 
		<a class="action-button" href="${h.url_for( action='add' )}">
	        <img src="${h.url_for('/static/images/silk/add.png')}" />
	        <span>add credentials</span>
	    </a>
		 or 
		<a href="http://aws.amazon.com/" target="_blank">
	        open AWS account with Amazon</a>.
	%endif

%else:
	You have no cloud providers registered with your Galaxy account:
	<a class="action-button" href="${h.url_for( action='add_provider' )}">
        <img src="${h.url_for('/static/images/silk/add.png')}" />
        <span>add provider now</span>
    </a>
%endif