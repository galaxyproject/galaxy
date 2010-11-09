<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/requests/common/common.mako" import="render_sample_datasets" />

${h.js( "ui.core", "jquery.cookie", "jquery.dynatree" )}
<link href='/static/june_2007_style/blue/dynatree_skin/ui.dynatree.css' rel='stylesheet' type='text/css'>
##${h.js( "jquery.dynatree" )}

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
		        document.select_datasets_to_transfer.selected_datasets_to_transfer.value = selKeys.join(",")
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

<%
    is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
    can_transfer_datasets = is_admin and sample.untransferred_dataset_files
%>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" href="${h.url_for( controller='requests_admin', action='view_request_type', id=trans.security.encode_id( request.type.id ) )}">Sequencer configuration</a></li>
    %if can_transfer_datasets:
        <li><a class="action-button" href="${h.url_for( controller='requests_admin', action='manage_datasets', cntrller=cntrller, sample_id=trans.security.encode_id( sample.id ) )}">Transfer datasets</a></li>
    %endif
    <li><a class="action-button" href="${h.url_for( controller='requests_common', action='view_request', cntrller=cntrller, id=trans.security.encode_id( request.id ) )}">Browse this request</a></li>
</ul>

%if not sample:
    <font color="red"><b><i>Select a sample before selecting datasets to transfer</i></b></font>
    <br/><br/>
%endif

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Select datasets to transfer from data directory configured for the sequencer</div>
    <form name="select_datasets_to_transfer" id="select_datasets_to_transfer" action="${h.url_for( controller='requests_admin', action='select_datasets_to_transfer', cntrller=cntrller, request_id=trans.security.encode_id( request.id ))}" method="post" >
        <div class="form-row">
            <label>Sample:</label>
            ${sample_id_select_field.get_html()}
            <div class="toolParamHelp" style="clear: both;">
                Select the sample that was sequenced to produce the datasets you want to transfer.
            </div>
        </div>
        <div class="form-row" >
            <label>Select datasets from source data location defined in the sequencer configuration:</label>
            <div id="tree" >
                Loading...
            </div>
            <input id="selected_datasets_to_transfer" name="selected_datasets_to_transfer" type="hidden" size=40"/>
            <div class="toolParamHelp" style="clear: both;">
                <ul>
                    <li>Click the <b>Sequencer configuration</b> button and change the <b>Data directory</b> setting to redefine the source data location.</li>
                    <li>Select a folder to select all of the individual files within that folder.</li>
                    <li>Click the <b>Select datasets</b> button when desired dataset check boxes are checked.</li>
                </ul>
            </div>            
        </div>
        <div class="form-row">
            <div id="file_details" class="toolParamHelp" style="clear: both;background-color:#FAFAFA;"></div>
        </div>
        <div class="form-row">
            <input type="submit" name="select_datasets_to_transfer_button" value="Select datasets"/>
        </div>
    </form>
</div>

%if sample and sample.datasets:
    <% title = 'Datasets currently selected for "sample.name"' %>
    <p/>
    ${render_sample_datasets( 'requests_admin', sample, sample.datasets, title )}
%endif
