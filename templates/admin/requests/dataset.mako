<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if message:
    ${render_msg( message, status )}
%endif

<br/>
<br/>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_common', action='show_datatx_page', cntrller='requests_admin', sample_id=trans.security.encode_id(sample.id) )}">
        <span>Dataset transfer page</span></a>
    </li>
</ul>

<div class="toolForm">
    <div class="toolFormTitle">Dataset details</div>
    <div class="toolFormBody">
        <form name="dataset_details" action="${h.url_for( controller='requests_admin', action='dataset_details', save_changes=True, sample_id=trans.security.encode_id(sample.id), dataset_index=dataset_index )}" method="post" >
            <%
                dataset = sample.dataset_files[dataset_index]
            %>
            <div class="form-row">
                <label>Name:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    %if dataset['status'] in [sample.transfer_status.IN_QUEUE, sample.transfer_status.NOT_STARTED]:
                        <input type="text" name="name" value="${dataset['name']}" size="60"/>
                    %else:
                        ${dataset['name']}
                    %endif
                    
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>File on the Sequencer:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    ${dataset['filepath']}
                    ##<input type="text" name="filepath" value="${dataset['filepath']}" size="100" readonly/>
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Size:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    ${dataset.get('size', 'Unknown')}
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Transfer status:</label>
                <div style="float: left; width: 250px; margin-right: 10px;">
                    ${dataset['status']}
                    <br/>
                    %if dataset['status'] == sample.transfer_status.ERROR:
                        ${dataset['error_msg']}
                    %endif 
                </div>
                <div style="clear: both"></div>
            </div>
            %if dataset['status'] in [sample.transfer_status.IN_QUEUE, sample.transfer_status.NOT_STARTED]:
                <div class="form-row">
                    <input type="submit" name="save" value="Save"/>
                </div>
            %endif
        </form>
    </div>
</div>