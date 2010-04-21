<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if message:
    ${render_msg( message, status )}
%endif

<script type="text/javascript">
$(document).ready(function(){
    //hide the all of the element with class msg_body
    $(".msg_body").hide();
    //toggle the componenet with class msg_body
    $(".msg_head").click(function(){
        $(this).next(".msg_body").slideToggle(450);
    });
});
</script>
<style type="text/css">
.msg_head {
    padding: 0px 0px;
    cursor: pointer;
}

}
</style>


<h2>Data transfer from Sequencer</h2>
<h3>Sample "${sample.name}" of Request "${sample.request.name}"</h3>

<ul class="manage-table-actions">
    %if sample.request.submitted() and sample.inprogress_dataset_files():
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_admin', action='show_datatx_page', sample_id=trans.security.encode_id(sample.id) )}">
        <span>Refresh this page</span></a>
    </li>
    %endif
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_admin', action='manage_request_types', operation='view', id=trans.security.encode_id(sample.request.type.id) )}">
        <span>Sequencer information</span></a>
    </li>
    <li>
        <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller='library_admin', id=trans.security.encode_id( sample.library.id ) )}">
        <span>${sample.library.name} Data Library</span></a>
    </li>
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_admin', action='list', operation='show_request', id=trans.security.encode_id(sample.request.id) )}">
        <span>Browse this request</span></a>
    </li>
</ul>

<div class="toolForm">
    %if len(dataset_files):
##    <form name="get_data" action="${h.url_for( controller='requests_admin', action='get_data', sample_id=sample.id)}" method="post" >
        <div class="form-row">
        <h4>Sample Dataset(s)</h4>
        %if sample.untransferred_dataset_files():
            <div class="form-row">
                <ul class="manage-table-actions">
                    <li>
                        <a class="action-button" href="${h.url_for( controller='requests_admin', action='get_data', start_transfer_button=True, sample_id=sample.id )}">
                        <span>Start transfer</span></a>
                    </li>
                </ul>
             </div>
         %endif
        <div class="form-row">
            <table class="grid">
            <thead>
                <tr>
                    <th>Dataset File</th>
                    <th>Transfer Status</th>
                    <th></th>
                </tr>
            <thead>
                <tbody>
                    %for dataset_index, dataset_file in enumerate(dataset_files):
                        ${sample_dataset_files( dataset_index, dataset_file['name'], dataset_file['status'] )}
                    %endfor
                </tbody>
            </table>
        </div>
        </div>

##    </form>
##</div>


<br/>
<br/>
%endif

##<div class="toolForm">
    <form name="get_data" action="${h.url_for( controller='requests_admin', action='get_data', sample_id=sample.id)}" method="post" >
        <div class="form-row">
            ##<div class="toolFormTitle">Select files for transfer</div>
            <h4>Select files for transfer</h4>
            <div style="width: 60%;">
                <div class="form-row">
                    <label>Folder path on the sequencer:</label>
                    <input type="text" name="folder_path" value="${folder_path}" size="100"/>
                    <input type="submit" name="browse_button" value="List contents"/>
                    <input type="submit" name="open_folder" value="Open folder"/>
                    <input type="submit" name="folder_up" value="Up"/>
                </div>
                <div class="form-row">
                <select name="files_list" id="files_list" style="max-width: 98%; width: 98%; height: 150px; font-size: 100%;" multiple>
                    %for index, f in enumerate(files):
                        <option value="${f}">${f}</option>
                    %endfor
                </select> 
                </div>
                <div class="form-row">
                    <div class="toolParamHelp" style="clear: both;">
                        After clicking <b>Transfer</b> do <i>not</i> close this page or 
                        navigate away from this page. Once the transfer is complete
                        the dataset(s) will show up on this page.
                    </div>
                    <input type="submit" name="select_files_button" value="Select"/>
                </div>
            </div>
        </div>
    </form>
</div>

<%def name="sample_dataset_files( dataset_index, dataset_name, status )">
    <tr>
        <td>
            <label class="msg_head"><a href="${h.url_for( controller='requests_admin', action='dataset_details', sample_id=trans.security.encode_id(sample.id), dataset_index=dataset_index )}">${dataset_name}</a></label>
##            <div class="msg_head"><u>${dataset_file.split('/')[-1]}</u></div>
##            <div class="msg_body">
##                ${dataset_file}
##            </div>
        </td>
        <td>
            %if status not in [sample.transfer_status.NOT_STARTED, sample.transfer_status.COMPLETE]: 
                <i>${status}</i>
            %else:
                ${status}
            %endif
        </td>
        ##<td></td>
        %if status == sample.transfer_status.NOT_STARTED: 
        <td>
            <a class="action-button" href="${h.url_for( controller='requests_admin', action='get_data', sample_id=sample.id, remove_dataset_button=True, dataset_index=dataset_index )}">
            <img src="${h.url_for('/static/images/delete_icon.png')}" />
            <span></span></a>
        </td>
        %else:
            <td></td>
        %endif
    </tr>
</%def>