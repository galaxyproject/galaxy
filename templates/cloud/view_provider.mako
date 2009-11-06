<%inherit file="/base.mako"/>

<%def name="title()">Cloud provider</%def>

<h2>Cloud provider details</h2>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( action='list' )}">
            <img src="${h.url_for('/static/images/silk/resultset_previous.png')}" />
            <span>Return to cloud management console</span>
        </a>
    </li>
</ul>
	
%if provider:
	${view_provider( provider )}
%else:
	There is no cloud provider under that name.
%endif




<%def name="view_provider( provider )">
	<table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
       <tr>
       		<td> Cloud provider name: </td>
			<td>
                ${provider.name}
                <a id="cp-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            </td>
			<td>
                <div popupmenu="cp-popup">
                <a class="action-button" href="${h.url_for( action='edit_provider', id=trans.security.encode_id(provider.id) )}">Edit</a>
                <a class="action-button" confirm="Are you sure you want to delete cloud provider '${provider.name}'?" href="${h.url_for( action='delete_provider', id=trans.security.encode_id(provider.id) )}">Delete</a>
                </div>
            </td>
       </tr>
	   <tr>
	   		<td> Last updated: </td>
			<td> ${str(provider.update_time)[:16]} 
	        	<%
					context.write( ' UTC (' )
					context.write( str(h.date.distance_of_time_in_words (provider.update_time, h.date.datetime.utcnow() ) ) )
				%> ago)
			</td>
	   </tr>
	   <tr>
	   		<td> Cloud provider type: </td>
			<td> ${str(provider.type)[:16]}</td>
	   </tr>
	   %if provider.region_connection != None:
	   		<tr>
		   		<td> Region connection: </td>
				<td> ${provider.region_connection} </td>
		   	</tr>
	   %endif
	   %if provider.region_name != None:
	   		<tr>
		   		<td> Region name: </td>
				<td> ${provider.region_name} </td>
		   	</tr>
	   %endif
	   %if provider.region_endpoint != None:
	   		<tr>
		   		<td> Region endpoint: </td>
				<td> ${provider.region_endpoint} </td>
		   	</tr>
	   %endif
	   %if provider.is_secure != None:
	   		<tr>
		   		<td> Is secure: </td>
				<td> ${provider.is_secure} </td>
		   	</tr>
	   %endif
	   %if provider.host != None:
	   		<tr>
		   		<td> Host: </td>
				<td> ${provider.host} </td>
		   	</tr>
	   %endif
	   %if provider.port != None:
	   		<tr>
		   		<td> Port: </td>
				<td> ${provider.port} </td>
		   	</tr>
	   %endif
	   %if provider.proxy != None:
	   		<tr>
		   		<td> Proxy: </td>
				<td> ${provider.proxy} </td>
		   	</tr>
	   %endif
	   %if provider.proxy_port != None:
	   		<tr>
		   		<td> Proxy port: </td>
				<td> ${provider.proxy_port} </td>
		   	</tr>
	   %endif
	   %if provider.proxy_pass != None:
	   		<tr>
		   		<td> Proxy pass: </td>
				<td> ${provider.proxy_pass} </td>
		   	</tr>
	   %endif
	   %if provider.debug != None:
	   		<tr>
		   		<td> Debug: </td>
				<td> ${provider.debug} </td>
		   	</tr>
	   %endif
	   %if provider.https_connection_factory != None:
	   		<tr>
		   		<td> HTTPS connection factory: </td>
				<td> ${provider.https_connection_factory} </td>
		   	</tr>
	   %endif
	   %if provider.path != None:
	   		<tr>
		   		<td> Path: </td>
				<td> ${provider.path} </td>
		   	</tr>
	   %endif
	</table>
</%def>
