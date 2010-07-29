<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


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
   function display_file_details(request_id, folder_path)
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
                data: { id: request_id, folder_path: document.get_data.folder_path.value+selected_value },
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
   function open_folder1(request_id, folder_path)
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
                data: { id: request_id, folder_path: document.get_data.folder_path.value },
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

%if message:
    ${render_msg( message, status )}
%endif
<br/>
<br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_admin', action='manage_request_types', operation='view', id=trans.security.encode_id(request.type.id) )}">
        <span>Sequencer information</span></a>
    </li>
    <li>
        <a class="action-button" href="${h.url_for( controller=cntrller, action='list', operation='show', id=trans.security.encode_id(request.id) )}">
        <span>Browse this request</span></a>
    </li>
</ul>

<form name="get_data" id="get_data" action="${h.url_for( controller='requests_admin', cntrller=cntrller, action='get_data', request_id=request.id)}" method="post" >
    <div class="toolFormTitle">Select files for transfer</div>
    <div class="toolForm">
        <div class="form-row">
            <label>Sample:</label>
            ${samples_selectbox.get_html()}
            <div class="toolParamHelp" style="clear: both;">
                Select the sample with which you want to associate the dataset(s)
            </div>
            <br/>
            <label>Folder path on the sequencer:</label>
            <input type="text" name="folder_path" value="${folder_path}" size="100"/>
            <input type="submit" name="browse_button" value="List contents"/>
            ##<input type="submit" name="open_folder" value="Open folder"/>
            <input type="submit" name="folder_up" value="Up"/>
        </div>
        <div class="form-row">
            <select name="files_list" id="files_list" style="max-width: 60%; width: 98%; height: 150px; font-size: 100%;" ondblclick="open_folder1(${request.id}, '${folder_path}')" onChange="display_file_details(${request.id}, '${folder_path}')" multiple>
                %for index, f in enumerate(files):
                    <option value="${f}">${f}</option>
                %endfor
            </select> 
            <br/>
            <div id="file_details" class="toolParamHelp" style="clear: both;">
                
            </div>
        </div>
        <div class="form-row">
<!--            <div class="toolParamHelp" style="clear: both;">
                After selecting dataset(s), be sure to click on the <b>Start transfer</b> button. 
                Once the transfer is complete the dataset(s) will show up on this page.
            </div>-->
            <input type="submit" name="select_show_datasets_button" value="Select & show datasets"/>
            <input type="submit" name="select_more_button" value="Select more"/>
        </div>
    </div>
</form>
