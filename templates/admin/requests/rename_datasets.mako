<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<% from galaxy.web.controllers.requests_admin import build_rename_datasets_for_sample_select_field %>

<h3>Rename datasets for Sample "${sample.name}"</h3>

<ul class="manage-table-actions">
    <li><a class="action-button" href="${h.url_for( controller='requests_admin', action='manage_datasets', sample_id=trans.security.encode_id( sample.id ) )}">Browse datasets</a></li>
    <li><a class="action-button" href="${h.url_for( controller='requests_common', action='view_request', cntrller='requests_admin', id=trans.security.encode_id( sample.request.id ) )}">Browse this request</a></li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
	<form name="rename_datasets" id="rename_datasets" action="${h.url_for( controller='requests_admin', action='rename_datasets', id_list=id_list, sample_id=trans.security.encode_id( sample.id ) )}" method="post" >

	    <table class="grid">
	        <thead>
	            <tr>
	                <th>Prepend directory name</th>
	                <th>Name</th>
	                <th>Path on external service</th>
	            </tr>
	        <thead>
	        <tbody>
	            %for id in id_list:
	               <% sample_dataset = trans.sa_session.query( trans.model.SampleDataset ).get( trans.security.decode_id( id ) ) %>
	               %if sample_dataset.status == trans.app.model.SampleDataset.transfer_status.NOT_STARTED:
		                <tr>
		                    <td>
		                        <% rename_datasets_for_sample_select_field = build_rename_datasets_for_sample_select_field( trans, sample_dataset ) %>
		                        ${rename_datasets_for_sample_select_field.get_html()}
		                    </td>
		                    <td>
		                        <input type="text" name="new_name_${trans.security.encode_id( sample_dataset.id ) }" value="${sample_dataset.name}" size="100"/>
		                    </td>
		                    <td>${sample_dataset.file_path}</td>
		                </tr>
	                %endif
	            %endfor
	        </tbody>
	    </table>
	    <br/>
        <div class="form-row">
	        <div class="toolParamHelp" style="clear: both;">
	            A dataset name should only contain the alphanumeric characters or underscore(_).
	            If a dataset name contains any other character, it would be replaced by an underscore(_).
	        </div>
        </div>
	    <div class="form-row">
		    <input type="submit" name="rename_datasets_button" value="Save"/>
		    <input type="submit" name="cancel_rename_datasets_button" value="Close"/>
	    </div>
	</form>

</div>
