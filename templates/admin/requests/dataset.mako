<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<br/><br/>

<% sample = sample_dataset.sample %>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_common', action='view_dataset_transfer', cntrller='requests_admin', sample_id=trans.security.encode_id( sample.id ) )}">
        <span>Browse datasets</span></a>
    </li>
</ul>

<div class="toolForm">
    <div class="toolFormTitle">Dataset Information</div>
    <div class="toolFormBody">
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    ${sample_dataset.name}
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>File on the Sequencer:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    ${sample_dataset.file_path}
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
                <label>Created on:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    ${sample_dataset.create_time}
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Updated on:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    ${sample_dataset.update_time}
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Transfer status:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    ${sample_dataset.status}
                    <br/>
                    %if sample_dataset.status == sample.transfer_status.ERROR:
                        ${sample_dataset.error_msg}
                    %endif 
                </div>
                <div style="clear: both"></div>
            </div>
    </div>
</div>