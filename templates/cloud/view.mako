<%inherit file="/base.mako"/>

<%def name="title()">Cloud credentials</%def>

<h2>Credentials details</h2>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( action='list' )}">
            <img src="${h.url_for('/static/images/silk/resultset_previous.png')}" />
            <span>Return to cloud management console</span>
        </a>
    </li>
</ul>
	
%if credDetails:
	${view_cred( credDetails )}
%else:
	There are no credentials under that name.
%endif




<%def name="view_cred( credDetails )">
	<table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
       <tr>
       		<td> Credentials name: </td>
			<td>
                ${credDetails.name}
                <a id="wf-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            </td>
			<td>
                <div popupmenu="wf-popup">
                <a class="action-button" href="${h.url_for( action='rename', id=trans.security.encode_id(credDetails.id) )}">Rename</a>
                <a class="action-button" confirm="Are you sure you want to delete credentials '${credDetails.name}'?" href="${h.url_for( action='delete', id=trans.security.encode_id(credDetails.id) )}">Delete</a>
                </div>
            </td>
       </tr>
	   <tr>
	   		<td> Last updated: </td>
			<td> ${str(credDetails.update_time)[:16]} 
	        	<%
					context.write( ' UTC (' )
					context.write( str(h.date.distance_of_time_in_words (credDetails.update_time, h.date.datetime.utcnow() ) ) )
				%> ago)
			</td>
	   </tr>
	   <tr>
	   		<td> Cloud provider type: </td>
			<td> ${str(credDetails.provider.type)[:16]}</td>
	   </tr>
	   <tr>
	   		<td> Cloud provider name: </td>
			<td> ${str(credDetails.provider.name)[:16]}</td>
	   </tr>
	   <tr>
	   		<td> Access key: </td>
			<td> 
				${credDetails.access_key}
			</td>
	   </tr>
	   <tr>
	   		<td> Secret key: </td>
			<td>
				<div id="shortComment2">
                   <a onclick="document.getElementById('fullComment2').style.display = 'block'; 
                    document.getElementById('shortComment2').style.display = 'none'; return 0" 
                    href="javascript:void(0)">
                    + Show
                   </a>                    
                </div>
                <div id="fullComment2" style="DISPLAY: none">
		      		<a onclick="document.getElementById('shortComment2').style.display = 'block'; 
                    document.getElementById('fullComment2').style.display = 'none'; return 0;" 
                    href="javascript:void(0)">
                    - Hide
                    </a><br />
					<nobr><b>${credDetails.secret_key}</b></nobr><br/>         
               </div>
			</td>
	   </tr>
	   <tr><td id="addl"><b>Additional cloud provider information (if available):</b></td></tr>
	   %if credDetails.provider.region_connection != None:
	   		<tr>
		   		<td> Region connection: </td>
				<td> ${credDetails.provider.region_connection} </td>
		   	</tr>
	   %endif
	   %if credDetails.provider.region_name != None:
	   		<tr>
		   		<td> Region name: </td>
				<td> ${credDetails.provider.region_name} </td>
		   	</tr>
	   %endif
	   %if credDetails.provider.region_endpoint != None:
	   		<tr>
		   		<td> Region endpoint: </td>
				<td> ${credDetails.provider.region_endpoint} </td>
		   	</tr>
	   %endif
	   %if credDetails.provider.is_secure != None:
	   		<tr>
		   		<td> Is secure: </td>
				<td> ${credDetails.provider.is_secure} </td>
		   	</tr>
	   %endif
	   %if credDetails.provider.host != None:
	   		<tr>
		   		<td> Host: </td>
				<td> ${credDetails.provider.host} </td>
		   	</tr>
	   %endif
	   %if credDetails.provider.port != None:
	   		<tr>
		   		<td> Port: </td>
				<td> ${credDetails.provider.port} </td>
		   	</tr>
	   %endif
	   %if credDetails.provider.proxy != None:
	   		<tr>
		   		<td> Proxy: </td>
				<td> ${credDetails.provider.proxy} </td>
		   	</tr>
	   %endif
	   %if credDetails.provider.proxy_port != None:
	   		<tr>
		   		<td> Proxy port: </td>
				<td> ${credDetails.provider.proxy_port} </td>
		   	</tr>
	   %endif
	   %if credDetails.provider.proxy_pass != None:
	   		<tr>
		   		<td> Proxy pass: </td>
				<td> ${credDetails.provider.proxy_pass} </td>
		   	</tr>
	   %endif
	   %if credDetails.provider.debug != None:
	   		<tr>
		   		<td> Debug: </td>
				<td> ${credDetails.provider.debug} </td>
		   	</tr>
	   %endif
	   %if credDetails.provider.https_connection_factory != None:
	   		<tr>
		   		<td> HTTPS connection factory: </td>
				<td> ${credDetails.provider.https_connection_factory} </td>
		   	</tr>
	   %endif
	   %if credDetails.provider.path != None:
	   		<tr>
		   		<td> Path: </td>
				<td> ${credDetails.provider.path} </td>
		   	</tr>
	   %endif
	</table>
</%def>
