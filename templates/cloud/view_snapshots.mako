<%inherit file="/base.mako"/>

<%def name="title()">Snapshots</%def>

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

%if snaps:
	<h2>Snapshots for instance ${snaps[0].uci.name}</h2>
%else:
	<h2>Selected instance has no recorded or associated snapshots.</h2>
%endif
 
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( action='list' )}">
            <img src="${h.url_for('/static/images/silk/resultset_previous.png')}" />
            <span>Return to cloud management console</span>
        </a>
    </li>
</ul>
 
%if snaps:
	<table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <colgroup width="2%"></colgroup>
		<colgroup width="16%"></colgroup>
		<colgroup width="16%"></colgroup>
		<colgroup width="10%"></colgroup>
		<colgroup width="5%"></colgroup>
		<tr class="header">
			<th>#</th>
            <th>Create time</th>
			<th>Snapshot ID</th>
			<th>Status</th>
			<th>Delete?</th>
			<th></th>
        </tr>
		<%
			total_hours = 0
		%>
        %for i, snap in enumerate( snaps ):
            <tr>
            	<td>${i+1}</td>
                <td>
				%if snap.create_time:
					${str(snap.create_time)[:16]} UCT
				%else:
					N/A
				%endif
				</td>
				<td>
				%if snap.snapshot_id:
					${snap.snapshot_id}
				%else:
					N/A
				%endif
				</td>
				<td>
				%if snap.status:
					${snap.status}
				%else:
					N/A
				%endif
				</td>
				<td>
					<a confirm="Are you sure you want to delete snapshot '${snap.snapshot_id}'?" 
					   href="${h.url_for( controller='cloud', action='delete_snapshot', uci_id=trans.security.encode_id(snap.uci.id), snap_id=trans.security.encode_id(snap.id) )}">x</a>
				</td>
            </tr>
        %endfor
    </table>
%endif





