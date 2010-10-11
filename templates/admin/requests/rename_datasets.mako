<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif
<h3>Rename datasets for Sample "${sample.name}"</h3>
<br/>
${render_msg('A dataset can be renamed only if its status is "Not Started"', 'ok')}

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_admin', action='manage_datasets', sample_id=trans.security.encode_id( sample.id ) )}">Browse datasets</a>
    </li>
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_common', action='manage_request', cntrller=cntrller, id=trans.security.encode_id( sample.request.id ) )}">Browse this request</a>
    </li>
</ul>

<form name="rename_datasets" id="rename_datasets" action="${h.url_for( controller='requests_admin', action='rename_datasets', id_list=id_list, sample_id=trans.security.encode_id( sample.id ) )}" method="post" >
    <table class="grid">
    <thead>
        <tr>
            <th>Prepend directory name</th>
            <th>Name</th>
            <th>Path on Sequencer</th>
        </tr>
    <thead>
        <tbody>
            %for id in id_list:
                <%
                    sample_dataset = trans.sa_session.query( trans.app.model.SampleDataset ).get( trans.security.decode_id(id) )
                    import os 
                    id = trans.security.decode_id(id) 
                %>
                %if sample_dataset.status == trans.app.model.Sample.transfer_status.NOT_STARTED:
	                <tr>
	                    <td>
			                <select name="prepend_${sample_dataset.id}" last_selected_value="2">
			                    <option value="None" selected></option>
			                    %for option_index, option in enumerate(sample_dataset.file_path.split(os.sep)[:-1]):
			                        %if option.strip():
    	                               <option value="${option}">${option}</option>
    	                            %endif
			                    %endfor
			                </select>
	                    </td>
	                    <td>
	                        <input type="text" name="name_${sample_dataset.id}" value="${sample_dataset.name}" size="100"/>
	                    </td>
	                    <td>
	                        ${sample_dataset.file_path}
	                    </td>
	                </tr>
	            %endif 
            %endfor
        </tbody>
    </table>
    <br/>
    <div class="form-row">
	    <input type="submit" name="save_button" value="Save"/>
	    <input type="submit" name="cancel_button" value="Close"/>
    </div>
</form>
