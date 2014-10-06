<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<br/><br/>

<%
    sample = sample_dataset.sample
    is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
    can_manage_datasets = is_admin and sample.untransferred_dataset_files
%>

<ul class="manage-table-actions">
    %if can_manage_datasets:
        <li><a class="action-button" href="${h.url_for( controller='requests_admin', action='manage_datasets', cntrller=cntrller, sample_id=trans.security.encode_id( sample.id ) )}">Manage sample datasets</a></li>
    %endif
    <li><a class="action-button" href="${h.url_for( controller='requests_common', action='view_request', cntrller=cntrller, id=trans.security.encode_id( sample.request.id ) )}">Browse this request</a></li>
</ul>

<div class="toolForm">
    <div class="toolFormTitle">"${sample.name}" Dataset</div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Name:</label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                ${sample_dataset.name}
            </div>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>External service:</label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                ${sample_dataset.external_service.name} (${sample_dataset.external_service.get_external_service_type( trans ).name})
            </div>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>File path:</label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                ${sample_dataset.file_path}
            </div>
            <div class="toolParamHelp" style="clear: both;">
                This file is contained in a sub-directory of the data directory configured for the external service.
            </div>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Size:</label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                ${sample_dataset.size}
            </div>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Date this dataset was selected for this sample:</label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                ${sample_dataset.create_time}
            </div>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Transfer status:</label>
            <div style="float: left; width: 250px; margin-right: 10px;">
                ${sample_dataset.status}
            </div>
            <div style="clear: both"></div>
        </div>
        %if sample_dataset.status == trans.app.model.SampleDataset.transfer_status.ERROR:
            <div class="form-row">
                 <label>Transfer error:</label>
                ${sample_dataset.error_msg}
            </div>
            <div style="clear: both"></div>
        %endif
    </div>
</div>
