<%inherit file="/base.mako"/>
<%def name="title()">Live instance details</%def>


<h2>Live instance details</h2>

%if liveInstance:
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
       		<td> Instance name: </td>
			<td>
                ${liveInstance.name}
                <a id="li-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            </td>
			<td>
                <div popupmenu="li-popup">
                <a class="action-button" href="${h.url_for( action='renameInstance', id=trans.security.encode_id(liveInstance.id) )}">Rename</a>
                <a class="action-button" confirm="Are you sure you want to stop instance '${liveInstance.name}'?" href="${h.url_for( action='stop', id=trans.security.encode_id(liveInstance.id) )}">Stop</a>
                </div>
            </td>
       </tr>
	   <tr>
	   		<td> Date created: </td>
			<td> ${str(liveInstance.create_time)[:16]} 
	        	<%
					context.write( ' UTC (' )
					context.write( str(h.date.distance_of_time_in_words (liveInstance.create_time, h.date.datetime.utcnow() ) ) )
				%> ago)
			</td>
	   </tr>
	   <tr>
	   		<td> Alive since: </td>
			<td> ${str(liveInstance.launch_time)[:16]} 
	        	<%
					context.write( ' UTC (' )
					context.write( str(h.date.distance_of_time_in_words (liveInstance.launch_time, h.date.datetime.utcnow() ) ) )
				%> ago)
			</td>
	   </tr>
	   %if liveInstance.instance_id != None:
	   		<tr>
		   		<td> Instance ID: </td>
				<td> ${liveInstance.instance_id} </td>
		   	</tr>
	   %endif
	   %if liveInstance.reservation_id != None:
	   <tr>
	   		<td> Reservation ID: </td>
			<td> ${liveInstance.reservation_id} </td>
	   </tr>
	   %endif
	   <tr>
	   		<td> AMI: </td>
	   		<td> ${liveInstance.ami} </td>
	   </tr>
	   <tr>
	   		<td> State:</td>
			<td> ${liveInstance.state} </td>
	   </tr>
	   <tr>
	   		<td> Public DNS:</td>
			<td> ${liveInstance.public_dns} </td>
	   </tr>
	   %if liveInstance.private_dns != None:
	   <tr>
	   		<td> Private DNS:</td>
			<td> ${liveInstance.private_dns} </td>
	   </tr>
	   %endif
	   %if liveInstance.availability_zone != None:
	   <tr>
	   		<td> Availabilty zone:</td>
			<td> ${liveInstance.availability_zone} </td>
	   </tr>
	   %endif
	   %if liveInstance.keypair_fingerprint != None:
	   <tr>
	   		<td> Keypair fingerprint:</td>
			<td> ${liveInstance.keypair_fingerprint} </td>
	   </tr>
	   %endif
	   %if liveInstance.keypair_material != None:
	   <tr>
	   		<td> Keypair private key:</td>
			<td>
				<div id="shortComment2">
                   <a onclick="document.getElementById('fullComment2').style.display = 'block'; 
                    document.getElementById('shortComment2').style.display = 'none'; return 0" 
                    href="javascript:void(0)">
                    + Show
                   </a>                    
                </div>
                <div id="fullComment2" style="DISPLAY: none">
		      		<nobr><b>${liveInstance.keypair_material}</b></nobr><br/>
                    <a onclick="document.getElementById('shortComment2').style.display = 'block'; 
                    document.getElementById('fullComment2').style.display = 'none'; return 0;" 
                    href="javascript:void(0)">
                    - Hide
                    </a>            
               </div>
			</td>
	   </tr>
	   %endif
	</table>
%else:
	There is no live instance under that name.
%endif
