<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
${h.js( "ui.core", "jquery.cookie" )}
<link href='/static/june_2007_style/blue/dynatree_skin/ui.dynatree.css' rel='stylesheet' type='text/css'>
${h.js( "jquery.dynatree" )}

<script type="text/javascript">
    $(function(){
	    $("#tree").ajaxComplete(function(event, XMLHttpRequest, ajaxOptions) {
	        _log("debug", "ajaxComplete: %o", this); // dom element listening
	    });
        // --- Initialize sample trees
        $("#tree").dynatree({
            title: "${request.type.datatx_info['data_dir']}",
			rootVisible: true,
			minExpandLevel: 0, // 1: root node is not collapsible
			persist: false,
			checkbox: true,
			selectMode: 3,
            onPostInit: function(isReloading, isError) {
//                alert("reloading: "+isReloading+", error:"+isError);
               logMsg("onPostInit(%o, %o) - %o", isReloading, isError, this);
               // Re-fire onActivate, so the text is updated
               this.reactivate();
            }, 
            fx: { height: "toggle", duration: 200 },
                // initAjax is hard to fake, so we pass the children as object array:
                initAjax: {url: "${h.url_for( controller='requests_admin', action='open_folder' )}",
                           dataType: "json", 
                           data: { id: "${request.id}", key: "${request.type.datatx_info['data_dir']}" },
                       },
                onLazyRead: function(dtnode){
                    dtnode.appendAjax({
                        url: "${h.url_for( controller='requests_admin', action='open_folder' )}", 
                        dataType: "json",
                        data: { id: "${request.id}", key: dtnode.data.key },
                    });
                },
		      onSelect: function(select, dtnode) {
		        // Display list of selected nodes
		        var selNodes = dtnode.tree.getSelectedNodes();
		        // convert to title/key array
		        var selKeys = $.map(selNodes, function(node){
		             return node.data.key;
		        });
		        document.get_data.selected_files.value = selKeys.join(",")
		      },
		      onActivate: function(dtnode) {
		        var cell = $("#file_details");
		        var selected_value = dtnode.data.key
		        if(selected_value.charAt(selected_value.length-1) != '/') {
		            // Make ajax call
		            $.ajax( {
		                type: "POST",
		                url: "${h.url_for( controller='requests_admin', action='get_file_details' )}",
		                dataType: "json",
		                data: { id: "${request.id}", folder_path: dtnode.data.key },
		                success : function ( data ) {
		                    cell.html( '<label>'+data+'</label>' )
		                }
	                });
                } else {
                    cell.html( '' )
                }
		      },
        });    
    });

</script>

<br/>
<br/>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_admin', action='view_request_type', id=trans.security.encode_id( request.type.id ) )}">Sequencer configuration "${request.type.name}"</a>
    </li>
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_common', action='view_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Browse this request</a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Select files for transfer</div>
    <form name="get_data" id="get_data" action="${h.url_for( controller='requests_admin', action='get_data', cntrller=cntrller, request_id=trans.security.encode_id( request.id ))}" method="post" >
        <div class="form-row">
            <label>Sample:</label>
            ${sample_id_select_field.get_html()}
            <div class="toolParamHelp" style="clear: both;">
                Select the sample with which you want to associate the datasets
            </div>
        </div>
        <div class="form-row" >
            <label>Select dataset files in the sequencer:</label>
            <div id="tree" >
                Loading...
            </div>
            <input  id="selected_files" name="selected_files" type="hidden" size=40"/>
            <div class="toolParamHelp" style="clear: both;">
                To select a folder, select all the individual files in that folder.
            </div>            
        </div>
        <div class="form-row">
            <div id="file_details" class="toolParamHelp" style="clear: both;background-color:#FAFAFA;"></div>
        </div>
        <div class="form-row">
            <input type="submit" name="select_show_datasets_button" value="Select & show datasets"/>
            <input type="submit" name="select_more_button" value="Select more"/>
        </div>
    </form>
</div>
