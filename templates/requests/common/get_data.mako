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

<script type="text/javascript">
   function display_file_details(sample_id, folder_path)
   {
       var w = document.get_data.files_list.selectedIndex;
       var selected_value = document.get_data.files_list.options[w].value;
       var cell = $("#file_details");
       if(selected_value.charAt(selected_value.length-1) != '/')
       {
            // Make ajax call
            $.ajax( {
                type: "POST",
                url: "${h.url_for( controller='requests_admin', action='get_file_details' )}",
                dataType: "json",
                data: { id: sample_id, folder_path: document.get_data.folder_path.value+selected_value },
                success : function ( data ) {
                    cell.html( '<label>'+data+'</label>' )
                }
            });
        }
        else 
        {
            cell.html( '' )
        }
        
       
   }
</script>

<script type="text/javascript">
   function open_folder1(sample_id, folder_path)
   {
       var w = document.get_data.files_list.selectedIndex;
       var selected_value = document.get_data.files_list.options[w].value;
       var cell = $("#file_details");
       if(selected_value.charAt(selected_value.length-1) == '/')
       {
           document.get_data.folder_path.value = document.get_data.folder_path.value+selected_value
            // Make ajax call
            $.ajax( {
                type: "POST",
                url: "${h.url_for( controller='requests_admin', action='open_folder' )}",
                dataType: "json",
                data: { id: sample_id, folder_path: document.get_data.folder_path.value },
                success : function ( data ) {
                    document.get_data.files_list.options.length = 0
                    for(i=0; i<data.length; i++) 
                    {
                        var newOpt = new Option(data[i], data[i]);
                        document.get_data.files_list.options[i] = newOpt;
                    }
                    //cell.html( '<label>'+data+'</label>' )
                    
                }
            });
       }
        else 
        {
            cell.html( '' )
        }
   }
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
<br/>
<br/>

<ul class="manage-table-actions">
    %if sample.request.submitted() and sample.inprogress_dataset_files():
        <li>
            <a class="action-button" href="${h.url_for( controller='requests_common', cntrller=cntrller, action='show_datatx_page', sample_id=trans.security.encode_id(sample.id) )}">
            <span>Refresh this page</span></a>
        </li>
    %endif
    %if cntrller == 'requests_admin' and trans.user_is_admin():
        <li>
            <a class="action-button" href="${h.url_for( controller='requests_admin', action='manage_request_types', operation='view', id=trans.security.encode_id(sample.request.type.id) )}">
            <span>Sequencer information</span></a>
        </li>
    
        <li>
            <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller='library_admin', id=trans.security.encode_id( sample.library.id ) )}">
            <span>${sample.library.name} Data Library</span></a>
        </li>
    %else:
        <li>
            <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller='library', id=trans.security.encode_id( sample.library.id ) )}">
            <span>${sample.library.name} Data Library</span></a>
        </li>
    %endif
    <li>
        <a class="action-button" href="${h.url_for( controller=cntrller, action='list', operation='show', id=trans.security.encode_id(sample.request.id) )}">
        <span>Browse this request</span></a>
    </li>
</ul>


%if len(dataset_files):
    <h3>Sample Dataset(s)</h3>
    %if sample.untransferred_dataset_files() and cntrller == 'requests_admin':
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
%else:
    <div class="form-row">
        There are no dataset files associated with this sample.
    </div>
%endif

<br/>
<br/>

%if cntrller == 'requests_admin' and trans.user_is_admin():
    <form name="get_data" id="get_data" action="${h.url_for( controller='requests_admin', cntrller=cntrller, action='get_data', sample_id=sample.id)}" method="post" >
            <div class="toolFormTitle">Select files for transfer</div>
            ##<h4>Select files for transfer</h4>
            <div class="toolForm">
                <div class="form-row">
                    <label>Folder path on the sequencer:</label>
                    <input type="text" name="folder_path" value="${folder_path}" size="100"/>
                    <input type="submit" name="browse_button" value="List contents"/>
                    ##<input type="submit" name="open_folder" value="Open folder"/>
                    <input type="submit" name="folder_up" value="Up"/>
                </div>
                <div class="form-row">
                    <select name="files_list" id="files_list" style="max-width: 60%; width: 98%; height: 150px; font-size: 100%;" ondblclick="open_folder1(${sample.id}, '${folder_path}')" onChange="display_file_details(${sample.id}, '${folder_path}')" multiple>
                        %for index, f in enumerate(files):
                            <option value="${f}">${f}</option>
                        %endfor
                    </select> 
                    <br/>
                    <div id="file_details" class="toolParamHelp" style="clear: both;">
                        
                    </div>
                </div>
                <div class="form-row">
                    <div class="toolParamHelp" style="clear: both;">
                        After selecting dataset(s), be sure to click on the <b>Start transfer</b> button. 
                        Once the transfer is complete the dataset(s) will show up on this page.
                    </div>
                    <input type="submit" name="select_files_button" value="Select"/>
                </div>
            </div>
    </form>
%endif




<%def name="sample_dataset_files( dataset_index, dataset_name, status )">
    <tr>
        
        <td>
            %if cntrller == 'requests_admin' and trans.user_is_admin():
                <label class="msg_head"><a href="${h.url_for( controller='requests_admin', action='dataset_details', sample_id=trans.security.encode_id(sample.id), dataset_index=dataset_index )}">${dataset_name}</a></label>
            %else:
                ${dataset_name}
            %endif
        </td>
        <td>
            %if status not in [sample.transfer_status.NOT_STARTED, sample.transfer_status.COMPLETE]: 
                <i>${status}</i>
            %else:
                ${status}
            %endif
        </td>
        ##<td></td>
        %if status == sample.transfer_status.NOT_STARTED and cntrller == 'requests_admin' and trans.user_is_admin(): 
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
