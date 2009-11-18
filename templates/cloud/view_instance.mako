<%inherit file="/base.mako"/>
<%def name="title()">Live instance details</%def>

<%
	# Because of the one-to-many relationship between liveInstance (i.e., UCI) and actual instances, need to know
	#  which one is currently active. Because only one instance of UCI can be alive at any point in time, simply
	#  select the most recent one. 
	#  TODO: Once individual UCI's will be able to start more than one instance, this will need to be fixed
	#i_id = len(liveInstance.instance) - 1
%>

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
                ${liveInstance.uci.name}
                <a id="li-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            </td>
			<td>
                <div popupmenu="li-popup">
                <a class="action-button" href="${h.url_for( action='rename_uci', id=trans.security.encode_id(liveInstance.uci.id) )}">Rename</a>
                <a class="action-button" confirm="Are you sure you want to stop instance '${liveInstance.uci.name}'?" href="${h.url_for( action='stop', id=trans.security.encode_id(liveInstance.uci.id) )}">Stop</a>
                </div>
            </td>
       </tr>
	   <tr>
	   		<td> Date created: </td>
			<td> ${str(liveInstance.uci.create_time)[:16]} 
	        	<%
					context.write( ' UTC (' )
					context.write( str(h.date.distance_of_time_in_words (liveInstance.uci.create_time, h.date.datetime.utcnow() ) ) )
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
	   		<td> ${liveInstance.image.image_id} </td>
	   </tr>
	   <tr>
	   		<td> State:</td>
			<td> ${liveInstance.state} </td>
	   </tr>
	   <tr>
	   		<td> Type:</td>
			<td> ${liveInstance.type} </td>
	   </tr>
	   <tr>
	   		<td> Storage size:</td>
			<td> ${liveInstance.uci.total_size} </td>
	   </tr>
	   %if liveInstance.public_dns != None and liveInstance.public_dns != '':
	   <tr>
	   		<td> Public DNS:</td>
			<%
				lnk="http://"+str(liveInstance.public_dns)
			%>
			<td> <a href="${lnk}" target="_blank">${liveInstance.public_dns}</a></td>
	   </tr>
	   %endif
	   %if liveInstance.private_dns != None and liveInstance.private_dns != '':
	   <tr>
	   		<td> Private DNS:</td>
			<td> ${liveInstance.private_dns}</td>
	   </tr>
	   %endif
	   %if liveInstance.security_group != None:
	   <tr>
	   		<td> Security group zone:</td>
			<td> ${liveInstance.security_group} </td>
	   </tr>
	   %endif
	   %if liveInstance.availability_zone != None:
	   <tr>
	   		<td> Availabilty zone:</td>
			<td> ${liveInstance.availability_zone} </td>
	   </tr>
	   %endif
	   %if liveInstance.uci.key_pair_name != None:
	   <tr>
	   		<td> Keypair file name:</td>
			<td> ${liveInstance.uci.key_pair_name} </td>
	   </tr>
	   %endif
	   %if liveInstance.uci.key_pair_material != None:
	   <tr>
	   		<td> Keypair material:</td>
			<td>
			<div id="short">
               <a onclick="document.getElementById('full').style.display = 'block'; 
                document.getElementById('short').style.display = 'none'; return 0" 
                href="javascript:void(0)">
                + Show
               </a>                    
            </div>
            <div id="full" style="DISPLAY: none">
	      		<a onclick="document.getElementById('short').style.display = 'block'; 
                document.getElementById('full').style.display = 'none'; return 0;" 
                href="javascript:void(0)">
                - Hide</a>
                ${liveInstance.uci.key_pair_material}<br/>
            </div>
			</td>
	   </tr>
	   %endif
	   
	</table>
%else:
	There is no live instance under that name.
%endif
