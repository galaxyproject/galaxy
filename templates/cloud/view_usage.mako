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

%if prevInstances:
	<h2>Usage report for instance ${prevInstances[0].uci.name}</h2>
%else:
	<h2>Selected instance has no record of being used.</h2>
%endif
 
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( action='list' )}">
            <img src="${h.url_for('/static/images/silk/resultset_previous.png')}" />
            <span>Return to cloud management console</span>
        </a>
    </li>
</ul>
 
%if prevInstances:
	<table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <colgroup width="2%"></colgroup>
		<colgroup width="16%"></colgroup>
		<colgroup width="16%"></colgroup>
		<colgroup width="10%"></colgroup>
		<colgroup width="5%"></colgroup>
		<tr class="header">
			<th>#</th>
            <th>Launch time</th>
			<th>Termination time</th>
			<th>Time alive</th>
			<th>Type</th>
            <th></th>
        </tr>
		<%
			total_hours = 0
		%>
        %for i, prevInstance in enumerate( prevInstances ):
            <tr>
            	<td>${i+1}</td>
                <td>
				%if prevInstance.launch_time:
					${str(prevInstance.launch_time)[:16]} UCT
				%else:
					N/A
				%endif
				</td>
				<td>
				%if prevInstance.stop_time:
					${str(prevInstance.stop_time)[:16]} UCT
				%else:
					N/A
				%endif
				</td>
				<td>
				<%
					# This is where current time and since duration is calculated
					if prevInstance.launch_time is None or prevInstance.stop_time is None:
						context.write( 'N/A' )
					else:
						context.write( str(h.date.distance_of_time_in_words (prevInstance.launch_time, prevInstance.stop_time ) ) )
						time_delta = prevInstance.stop_time - prevInstance.launch_time
						total_hours += time_delta.seconds / 3600
						if time_delta.seconds != 0:
							total_hours += 1
						
				%>
				</td>
				<td>${prevInstance.type}</td>
            </tr>
        %endfor
    </table>	
	<br/>Total number of hours instance was alive: ${total_hours} <br />
	Note that these are just best effort estimates - true usage should be obtained from respective cloud provider. <br />
	<%namespace name="view_cred" file="view.mako" />
	
	<div id="hide_cred_details">
       This instance uses credentials: 
	   <a onclick="document.getElementById('show_cred_details').style.display = 'block'; 
        document.getElementById('hide_cred_details').style.display = 'none'; return 0" 
        href="javascript:void(0)">
        ${prevInstances[0].uci.credentials.name}
       </a>                    
    </div>
    <div id="show_cred_details" style="DISPLAY: none">
  		This instance uses credentials: 
		<a onclick="document.getElementById('hide_cred_details').style.display = 'block'; 
        document.getElementById('show_cred_details').style.display = 'none'; return 0;" 
        href="javascript:void(0)">
        ${prevInstances[0].uci.credentials.name}
		</a>
		${view_cred.view_cred( prevInstances[0].uci.credentials ) }         
   </div>
	
	
%endif





