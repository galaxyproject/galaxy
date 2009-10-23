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

<h2>Instance usage report</h2>
 
%if prevInstances:
	<table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <colgroup width="2%"></colgroup>
		<colgroup width="20%"></colgroup>
		<colgroup width="20%"></colgroup>
		<colgroup width="5%"></colgroup>
		<tr class="header">
			<th>#</th>
            <th>Launch time</th>
			<th>Termination time</th>
			<th>Type</th>
            <th></th>
        </tr>
        %for i, prevInstance in enumerate( prevInstances ):
            <tr>
            	<td>${i+1}</td>
                <td>${str(prevInstance.launch_time)[:16]} UCT</td>
				<td>${str(prevInstance.stop_time)[:16]} UCT</td>
				<td>${prevInstance.type}</td>
            </tr>    
        %endfor
    </table>	
%else:
   Selected instance has no record of being used.
%endif