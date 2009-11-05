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

%if images:
	<h2>List of registered machine images:</h2>
 
	<table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <colgroup width="2%"></colgroup>
		<colgroup width="13%"></colgroup>
		<colgroup width="70%"></colgroup>
		<colgroup width="5%"></colgroup>
		<colgroup width="5%"></colgroup>
		<tr class="header">
			<th>#</th>
            <th>Machime image ID</th>
			<th>Manifest</th>
			<th>Edit</th>
			<th>Delete</th>
            <th></th>
        </tr>
		%for i, image in enumerate( images ):
            <tr>
            	<td>${i+1}</td>
                <td>
				%if image.image_id:
					${image.image_id}
				%else:
					N/A
				%endif
				</td>
				<td>
				%if image.manifest:
					${image.manifest}
				%else:
					N/A
				%endif
				</td>
				<td>
					<a href="${h.url_for( controller='cloud', action='editImage', image_id=image.image_id, manifest=image.manifest, id=trans.security.encode_id(image.id) )}">e</a>
				</td>
				<td>
					<a confirm="Are you sure you want to delete machine image '${image.image_id}'? Note that this may result in users' UCI's not to work any more!" 
					   href="${h.url_for( controller='cloud', action='deleteImage', id=trans.security.encode_id(image.id) )}">x</a>
				</td>
			</tr>
		%endfor
	</table>
%else:
	<h3>There are no registered machine images.</h3><br />
	<a href="${h.url_for( controller='cloud', action='addNewImage' )}" target="galaxy_main">Add machine image now?</a>

%endif





