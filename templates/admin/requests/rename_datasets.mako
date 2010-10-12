<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<% from galaxy.web.controllers.requests_admin import build_rename_datasets_for_sample_select_field %>

<br/><br/>
<font color="red"><b><i>A dataset can be renamed only if its status is "Not Started"</i></b></font>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_admin', action='manage_datasets', sample_id=trans.security.encode_id( sample.id ) )}">Browse datasets</a>
    </li>
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_common', action='manage_request', cntrller=cntrller, id=trans.security.encode_id( sample.request.id ) )}">Browse this request</a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Rename datasets for Sample "${sample.name}"</div>
    <div class="toolFormBody">
        <form name="rename_datasets" id="rename_datasets" action="${h.url_for( controller='requests_admin', action='rename_datasets', id_list=id_list, sample_id=trans.security.encode_id( sample.id ) )}" method="post" >
            <table class="grid">
                <thead>
                    <tr>
                        <th>Prepend directory name</th>
                        <th>Name</th>
                        <th>Path on sequencer</th>
                    </tr>
                <thead>
                <tbody>
                    %for sample_dataset in sample_datasets:
                        %if sample_dataset.status == trans.app.model.Sample.transfer_status.NOT_STARTED:
        	                <tr>
                                <td>
                                    <% rename_datasets_for_sample_select_field = build_rename_datasets_for_sample_select_field( trans, sample_dataset ) %>
                                    ${rename_datasets_for_sample_select_field}
        	                    </td>
        	                    <td>
        	                        <input type="text" name="new_name_${trans.security.encode_id( sample_dataset.id} )" value="${sample_dataset.name}" size="100"/>
        	                    </td>
        	                    <td>${sample_dataset.file_path}</td>
        	                </tr>
        	            %endif 
                    %endfor
                </tbody>
            </table>
            <br/>
            <div class="form-row">
        	    <input type="submit" name="rename_datasets_button" value="Save"/>
        	    <input type="submit" name="cancel_rename_datasets_button" value="Close"/>
            </div>
        </form>
    </div>
</div>
