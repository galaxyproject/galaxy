<%inherit file="/base.mako"/>
<%def name="title()">Cloud home</%def>


<h2>Credentials details</h2>

%if credDetails:
	<ul class="manage-table-actions">
	    <li>
	        <a class="action-button" href="${h.url_for( action='list' )}">
	            <img src="${h.url_for('/static/images/silk/resultset_previous.png')}" />
	            <span>Return to cloud management console</span>
	        </a>
	    </li>
	</ul>

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
	   		<td> Cloud provider: </td>
			<td> ${str(credDetails.provider_name)[:16]}</td>
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
		      		<nobr><b>${credDetails.secret_key}</b></nobr><br/>
                    <a onclick="document.getElementById('shortComment2').style.display = 'block'; 
                    document.getElementById('fullComment2').style.display = 'none'; return 0;" 
                    href="javascript:void(0)">
                    - Hide
                    </a>            
               </div>
			</td>
	   </tr>
	</table>
%else:
	There are no credentials under that name.
%endif
