<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/requests/common/sample_state.mako" import="render_sample_state" />
<%namespace file="/requests/common/sample_datasets.mako" import="render_sample_datasets" />



<script type="text/javascript">
$( function() {
    $( "select[refresh_on_change='true']").change( function() {
        var refresh = false;
        var refresh_on_change_values = $( this )[0].attributes.getNamedItem( 'refresh_on_change_values' )
        if ( refresh_on_change_values ) {
            refresh_on_change_values = refresh_on_change_values.value.split( ',' );
            var last_selected_value = $( this )[0].attributes.getNamedItem( 'last_selected_value' );
            for( i= 0; i < refresh_on_change_values.length; i++ ) {
                if ( $( this )[0].value == refresh_on_change_values[i] || ( last_selected_value && last_selected_value.value == refresh_on_change_values[i] ) ){
                    refresh = true;
                    break;
                }
            }
        }
        else {
            refresh = true;
        }
        if ( refresh ){
            $( "#show_request" ).submit();
        }
    });
});
</script>

<script type="text/javascript">
function showContent(vThis)
{
    // http://www.javascriptjunkie.com
    // alert(vSibling.className + " " + vDef_Key);
    vParent = vThis.parentNode;
    vSibling = vParent.nextSibling;
    while (vSibling.nodeType==3) { 
        // Fix for Mozilla/FireFox Empty Space becomes a TextNode or Something
        vSibling = vSibling.nextSibling;
    };
    if(vSibling.style.display == "none")
    {
        vThis.src="/static/images/fugue/toggle.png";
        vThis.alt = "Hide";
        vSibling.style.display = "block";
    } else {
        vSibling.style.display = "none";
        vThis.src="/static/images/fugue/toggle-expand.png";
        vThis.alt = "Show";
    }
    return;
}
</script>


<script type="text/javascript">
$(document).ready(function(){
    //hide the all of the element with class msg_body
    $(".msg_body").hide();
    //toggle the componenet with class msg_body
    $(".msg_head").click(function(){
        $(this).next(".msg_body").slideToggle(0);
    });
});
</script>

<script type="text/javascript">
    // Looks for changes in sample states using an async request. Keeps
    // calling itself (via setTimeout) until all samples are in a terminal
    // state.
    var updater = function ( sample_states ) {
        // Check if there are any items left to track
        var empty = true;
        for ( i in sample_states ) {
            empty = false;
            break;
        }
        if ( ! empty ) {
            setTimeout( function() { updater_callback( sample_states ) }, 1000 );
        }
    };
    var updater_callback = function ( sample_states ) {
        // Build request data
        var ids = []
        var states = []
        $.each( sample_states, function ( id, state ) {
            ids.push( id );
            states.push( state );
        });
        // Make ajax call
        $.ajax( {
            type: "POST",
            url: "${h.url_for( controller='requests_common', action='sample_state_updates' )}",
            dataType: "json",
            data: { ids: ids.join( "," ), states: states.join( "," ) },
            success : function ( data ) {
                $.each( data, function( id, val, cntrller ) {
                    // Replace HTML
                    var cell1 = $("#sampleState-" + id);
                    cell1.html( val.html_state );
                    var cell2 = $("#sampleDatasets-" + id);
                    cell2.html( val.html_datasets );
                    sample_states[ parseInt(id) ] = val.state;
                });
                updater( sample_states ); 
            },
            error: function() {
                // Just retry, like the old method, should try to be smarter
                updater( sample_states );
            }
        });
    };
    
	function checkAllFields()
	{
		var chkAll = document.getElementById('checkAll');
		var checks = document.getElementsByTagName('input');
		var boxLength = checks.length;
		var allChecked = false;
		var totalChecked = 0;
        if ( chkAll.checked == true )
        {
            for ( i=0; i < boxLength; i++ )
            {
	            if ( checks[i].name.indexOf( 'select_sample_' ) != -1)
	            {
	               checks[i].checked = true;
	            }
	        }
        }
        else
        {
            for ( i=0; i < boxLength; i++ )
            {
                if ( checks[i].name.indexOf( 'select_sample_' ) != -1)
                {
                   checks[i].checked = false
                }
            }
        }
	}

</script>

<style type="text/css">
.msg_head {
    padding: 0px 0px;
    cursor: pointer;
}
</style>

<script type="text/javascript">
    function stopRKey(evt) {
      var evt = (evt) ? evt : ((event) ? event : null);
      var node = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
      if ((evt.keyCode == 13) && (node.type=="text"))  {return false;}
    }
    document.onkeypress = stopRKey
</script> 

<% samples_not_ready = request.sequence_run_ready() %>
%if samples_not_ready:
    ${render_msg( "Select a target data library and folder for all the samples before starting the sequence run", "warning" )}
%endif

%if request.rejected():
    ${render_msg( "Reason for rejection: "+request.last_comment(), "warning" )}
%endif

%if message:
    ${render_msg( message, status )}
%endif

<div class="grid-header">
    <h2>Sequencing Request "${request.name}"</h2>
    <div class="toolParamHelp" style="clear: both;">
	    <b>Sequencer</b>: ${request.type.name} 
	    %if cntrller == 'requests_admin':
	        | <b>User</b>: ${request.user.email}
	    %endif
	    %if request.state() == request.states.SUBMITTED:
	        | <b>State</b>: <i>${request.state()}</i>
	    %else:
	        | <b>State</b>: ${request.state()}
	    %endif
    </div>
    
</div>
<br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="seqreq-${request.id}-popup" class="menubutton">Sequencing Request Actions</a></li>
    <div popupmenu="seqreq-${request.id}-popup">
        %if request.unsubmitted() and request.samples:
            <a class="action-button" confirm="More samples cannot be added to this request once it is submitted. Click OK to submit." href="${h.url_for( controller=cntrller, action='list', operation='Submit', id=trans.security.encode_id(request.id) )}">
            <span>Submit</span></a>
        %endif
        <a class="action-button" href="${h.url_for( controller=cntrller, action='list', operation='events', id=trans.security.encode_id(request.id) )}">
        <span>History</span></a>
        <a class="action-button"  href="${h.url_for( controller=cntrller, action='list', operation='Edit', id=trans.security.encode_id(request.id))}">
        <span>Edit</span></a>
        %if cntrller == 'requests_admin' and trans.user_is_admin():
            %if request.submitted():
                <a class="action-button" href="${h.url_for( controller=cntrller, action='list', operation='reject', id=trans.security.encode_id(request.id))}">
                <span>Reject</span></a>
                <a class="action-button" href="${h.url_for( controller='requests_admin', action='get_data', show_page=True, request_id=request.id)}">
                <span>Select dataset(s) to transfer</span></a>
            %endif
        %endif
    </div>
    <li>
        <a class="action-button"  href="${h.url_for( controller=cntrller, action='list')}">
        <span>Browse requests</span></a>
    </li>
</ul>



<div>
	<h4><img src="/static/images/fugue/toggle-expand.png" alt="Show" onclick="showContent(this);" style="cursor:pointer;"/> Request Information</h4>
	<div style="display:none;"  >
	    <table class="grid" border="0">
	        <tbody>
	            <tr>
		            <td valign="top" width="50%">
                        <div class="form-row">
                            <label>Description:</label>
                            %if request.desc:
                                ${request.desc}
                            %else:
                                <i>None</i>
                            %endif
                        </div>
                        <div style="clear: both"></div>
					    %for index, rd in enumerate(request_details):
					        <div class="form-row">
					            <label>${rd['label']}:</label>
					            %if not rd['value']:
					                <i>None</i>
					            %else:                      
					                %if rd['label'] == 'State':
					                    <a href="${h.url_for( controller=cntrller, action='list', operation='events', id=trans.security.encode_id(request.id) )}">${rd['value']}</a>
					                %else:
					                    ${rd['value']}     
					                %endif
					            %endif
					        </div>
					        <div style="clear: both"></div>
					    %endfor
					</td>
					<td valign="top" width="50%">
                        <div class="form-row">
                            <label>Date created:</label>
                            ${request.create_time}
                        </div>
                        <div class="form-row">
                            <label>Date updated:</label>
                            ${request.update_time}
                        </div>
	                    <div class="form-row">
	                        <label>Email notification recipient(s):</label>
	                        <% emails = ', '.join(request.notification['email']) %>
	                        %if emails:
	                            ${emails}
	                        %else:
	                            <i>None</i>
	                        %endif
	                    </div>
	                    <div style="clear: both"></div>
	                    <div class="form-row">
	                        <label>Email notification on sample state(s):</label>
	                        <% 
	                            states = []
	                            for ss in request.type.states:
	                                if ss.id in request.notification['sample_states']:
	                                    states.append(ss.name)
	                            states = ', '.join(states)
	                        %>
	                        %if states:
	                            ${states}
	                        %else:
	                            <i>None</i>
	                        %endif
	                    </div>
	                    <div style="clear: both"></div>
					</td>
				</tr>
		    </tbody>
		</table>
	    <div class="form-row">
		    <ul class="manage-table-actions">
		        <li>
		            <a class="action-button"  href="${h.url_for( controller=cntrller, action='list', operation='Edit', id=trans.security.encode_id(request.id))}">
		            <span>Edit request information</span></a>
		        </li>
		    </ul>
	    </div>
	</div>
</div>

<br/>

##<div class="toolForm">
    <form id="show_request" name="show_request" action="${h.url_for( controller='requests_common', cntrller=cntrller, action='request_page', edit_mode=edit_mode )}"  method="post" >
        ##<div class="form-row">
            %if current_samples:
                ## first render the basic info grid 
                ${render_basic_info_grid()}
		        %if not request.new() and edit_mode == 'False' and len(sample_ops.options) > 1:
                    <div class="form-row" style="background-color:#FAFAFA;">
	                    For selected sample(s): 
                        ${sample_ops.get_html()}
                    </div>
                    %if 'none' not in sample_ops.get_selected() and len(selected_samples):
                        <div class="form-row" style="background-color:#FAFAFA;">
                            %if trans.app.model.Sample.bulk_operations.CHANGE_STATE in sample_ops.get_selected():
                                <%
                                    widgets, title = request.type.change_state_widgets(trans)
                                %>
			                    %for w in widgets:
			                        <div class="form-row">
			                            <label>
			                                ${w[0]}:
			                            </label>
			                            ${w[1].get_html()}
			                            %if w[0] == 'Comments':
			                                <div class="toolParamHelp" style="clear: both;">
			                                    Optional
			                                </div>
			                            %endif
			                        </div>
			                    %endfor
		                        <div class="form-row">
		                            <input type="submit" name="change_state_button" value="Save"/>
		                            <input type="submit" name="change_state_button" value="Cancel"/>
		                        </div>
		                    %elif trans.app.model.Sample.bulk_operations.SELECT_LIBRARY in sample_ops.get_selected():
		                        <div class="form-row">
			                        <label>Select data library:</label>
			                        ${bulk_lib_ops[0].get_html()}
		                        </div>
		                        %if not 'none' in bulk_lib_ops[0].get_selected():
	                                <div class="form-row">
				                        <label>Select folder:</label>
				                        ${bulk_lib_ops[1].get_html()}
			                        </div>
			                        <div class="form-row">
			                          <input type="submit" name="change_lib_button" value="Save"/>
			                          <input type="submit" name="change_lib_button" value="Cancel"/>
	                                </div>
		                        %endif
                            %endif
                        </div>
                    %endif
		        %endif
                ## then render the other grid(s)
                <% trans.sa_session.refresh( request.type.sample_form ) %>
                %for grid_index, grid_name in enumerate(request.type.sample_form.layout):
                    ${render_grid( grid_index, grid_name, request.type.sample_form.fields_of_grid( grid_index ) )}
                %endfor
            %else:
                <label>There are no samples.</label>
            %endif
        ##</div>      
        %if request.samples and request.submitted():
            <script type="text/javascript">
                // Updater
                updater({${ ",".join( [ '"%s" : "%s"' % ( s.id, s.current_state().name ) for s in request.samples ] ) }});
            </script>
        %endif
        
        %if edit_mode == 'False':
            <table class="grid">
                <tbody>
                    <tr>
                        <div class="form-row">

                            %if request.unsubmitted():
                                <td>
                                    %if current_samples:
                                        <label>Copy </label>
                                        <input type="integer" name="num_sample_to_copy" value="1" size="3"/>
                                        <label>sample(s) from sample</label>
                                        ${sample_copy.get_html()}
                                    %endif
                                    <input type="submit" name="add_sample_button" value="Add New"/>
                                </td>
                            %endif
                            <td>
                                %if len(current_samples) and len(current_samples) <= len(request.samples):                     
                                    <input type="submit" name="edit_samples_button" value="Edit samples"/>
                                %endif
                            </td>
                        </div>
                    </tr> 
                </tbody>
            </table>
        %endif
        %if request.samples or current_samples: 
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="refresh" value="true" size="40"/>
                </div>
              <div style="clear: both"></div>
            </div>            
            %if edit_mode == 'True':   
                <div class="form-row">
                    <input type="submit" name="save_samples_button" value="Save"/>
                    <input type="submit" name="cancel_changes_button" value="Cancel"/>
                </div>
            %elif edit_mode == 'True' or len(current_samples) > len(request.samples):
                <div class="form-row">
                    <input type="submit" name="save_samples_button" value="Save"/>
                    <input type="submit" name="cancel_changes_button" value="Cancel"/>
                </div>
            %endif
            
        %endif
        <input type="hidden" name="id" value="${trans.security.encode_id(request.id)}" />
    </form>
##</div>

<br/>

%if request.unsubmitted():
    <form id="import" name="import" action="${h.url_for( controller='requests_common', action='request_page', edit_mode=edit_mode, request_id=trans.security.encode_id(request.id) )}" enctype="multipart/form-data" method="post" >
        <h4><img src="/static/images/fugue/toggle-expand.png" alt="Show" onclick="showContent(this);"  style="cursor:pointer;"/> Import samples</h4>
        <div style="display:none;">
            <input type="file" name="file_data" />
            <input type="submit" name="import_samples_button" value="Import samples"/>
            <br/>
            <div class="toolParamHelp" style="clear: both;">
                The csv file must be in the following format:<br/>
                SampleName,DataLibrary,DataLibraryFolder,FieldValue1,FieldValue2...
            </div>
        </div>
    </form>
##</div>
%endif



<%def name="render_grid( grid_index, grid_name, fields_dict )">
    <br/>
    <% if not grid_name:
          grid_name = "Grid "+ grid_index
    %>
    <div>
        %if edit_mode == 'True' or len(current_samples) > len(request.samples):
            <h4><img src="/static/images/fugue/toggle.png" alt="Show" onclick="showContent(this);"  style="cursor:pointer;"/> ${grid_name}</h4>
            <div>
        %else:
            <h4><img src="/static/images/fugue/toggle-expand.png" alt="Hide" onclick="showContent(this);"  style="cursor:pointer;"/> ${grid_name}</h4>
            <div style="display:none;">
        %endif
            <table class="grid">
                <thead>
                    <tr>
                        <th>Name</th>
                        %for index, field in fields_dict.items():
                            <th>
                                ${field['label']}
                                <div class="toolParamHelp" style="clear: both;">
                                    <i>${field['helptext']}</i>
                                </div>
                            </th>
                        %endfor
                        <th></th>
                    </tr>
                <thead>
                <tbody>
                    <%
                    trans.sa_session.refresh( request )
                    %>
                    %for sample_index, sample in enumerate(current_samples):
                        %if edit_mode == 'True':
                            <tr>
                                ${render_sample_form( sample_index, sample['name'], sample['field_values'], fields_dict)}
                            </tr>      
                        %else:
                            <tr>
                                %if sample_index in range(len(request.samples)):
                                    ${render_sample( sample_index, sample['name'], sample['field_values'], fields_dict )}
                                %else:                                                            
                                    ${render_sample_form( sample_index, sample['name'], sample['field_values'], fields_dict)}
                                %endif
                            </tr>  
                        %endif
                    %endfor
                </tbody>
            </table>
        </div>
    </div>
</%def>

## This function displays the "Basic Information" grid
<%def name="render_basic_info_grid()">
    <h3>Sample Information</h3>
    <table class="grid">
        <thead>
            <tr>
                <th><input type="checkbox" id="checkAll" name=select_all_samples value="true" onclick='checkAllFields(1);'><input type="hidden" name=select_all_samples value="true"></th>
                <th>Name</th>
                <th>Barcode</th>
                <th>State</th>
                <th>Data Library</th>
                <th>Folder</th>
                %if request.submitted() or request.complete(): 
                    <th>Dataset(s) Transferred</th>
                %endif
                <th></th>
            </tr>
        <thead>
        <tbody>
            <%
            trans.sa_session.refresh( request )
            %>
            %for sample_index, info in enumerate(current_samples):
                <% 
                    if sample_index in range(len(request.samples)):
                        sample = request.samples[sample_index]
                    else:
                        sample = None 
                %>
                %if edit_mode == 'True':
                    <tr>
                        ${show_basic_info_form( sample_index, sample, info )}
                    </tr>      
                %else:
                    <tr>
                        %if sample_index in range(len(request.samples)):
                            %if sample.id in selected_samples:
                                <td><input type="checkbox" name=select_sample_${sample.id} id="sample_checkbox" value="true" checked><input type="hidden" name=select_sample_${sample.id} id="sample_checkbox" value="true"></td>
                            %else:
                                <td><input type="checkbox" name=select_sample_${sample.id} id="sample_checkbox" value="true"><input type="hidden" name=select_sample_${sample.id} id="sample_checkbox" value="true"></td>
                            %endif
                            <td>${info['name']}</td>
                            <td>${info['barcode']}</td>
                            %if sample.request.unsubmitted():
                                <td>Unsubmitted</td>
                            %else:
                                <td id="sampleState-${sample.id}">${render_sample_state( cntrller, sample )}</td>
                            %endif
                            %if info['library']:
                                %if cntrller == 'requests':
                                    <td><a href="${h.url_for( controller='library_common', action='browse_library', cntrller='library', id=trans.security.encode_id( info['library'].id ) )}">${info['library'].name}</a></td>
                                %elif cntrller == 'requests_admin':
                                    <td><a href="${h.url_for( controller='library_common', action='browse_library', cntrller='library_admin', id=trans.security.encode_id( info['library'].id ) )}">${info['library'].name}</a></td>
                                %endif                                    
                            %else:
                                <td></td>
                            %endif
                            %if info['folder']:
                                <td>${info['folder'].name}</td>
                            %else:
                                <td></td>
                            %endif
                            %if request.submitted() or request.complete(): 
                                <td id="sampleDatasets-${sample.id}">
                                    ${render_sample_datasets( cntrller, sample )}
                                </td>
                            %endif
                            
                            
                        %else:                                                            
                            ${show_basic_info_form( sample_index, sample, info )}
                        %endif
                        %if request.unsubmitted() or request.rejected(): 
                            <td>
                                %if sample:
                                    %if sample.request.unsubmitted():
                                        <a class="action-button" href="${h.url_for( controller='requests_common', cntrller=cntrller, action='delete_sample', request_id=request.id, sample_id=sample_index )}">
                                        <img src="${h.url_for('/static/images/delete_icon.png')}"  style="cursor:pointer;"/>
                                        <span></span></a>
                                    %endif
                                %endif
                            </td>
                        %endif
                    </tr>  
                %endif
            %endfor
        </tbody>
    </table>
</%def>

<%def name="show_basic_info_form( sample_index, sample, info )">
    <td></td>
    <td>
        <input type="text" name=sample_${sample_index}_name value="${info['name']}" size="10"/>
        <div class="toolParamHelp" style="clear: both;">
            <i>${' (required)' }</i>
        </div>
    </td>
    %if cntrller == 'requests':
        %if sample:
            %if sample.request.unsubmitted():
                <td></td>
            %else:
                <td><input type="text" name=sample_${sample_index}_barcode value="${info['barcode']}" size="10"/></td>
            %endif
        %else:
            <td></td>
        %endif
    %elif cntrller == 'requests_admin':
        %if sample:
            %if sample.request.unsubmitted():
                <td></td>
            %else:
                <td><input type="text" name=sample_${sample_index}_barcode value="${info['barcode']}" size="10"/></td>
            %endif
        %else:
            <td></td>
        %endif
    %endif 
    %if sample:
        %if sample.request.unsubmitted():
            <td>Unsubmitted</td>
        %else:
            <td><a href="${h.url_for( controller='requests_admin', action='sample_events', sample_id=sample.id)}">${sample.current_state().name}</a></td>
        %endif    
    %else:
        <td></td>
    %endif
    <td>${info['lib_widget'].get_html()}</td>
    <td>${info['folder_widget'].get_html()}</td>
    %if request.submitted() or request.complete(): 
        %if sample:
            <td><a href="${h.url_for( controller='requests_admin', action='show_datatx_page', sample_id=trans.security.encode_id(sample.id) )}">${len(sample.datasets)}</a></td> 
        %else:
            <td><a href="${h.url_for( controller='requests_admin', action='show_datatx_page', sample_id=trans.security.encode_id(sample.id) )}">Add</a></td>
        %endif 
    %endif 
</%def>

<%def name="render_sample( index, sample_name, sample_values, fields_dict )">
    <td>
        ${sample_name}
    </td>
    %for field_index, field in fields_dict.items():
        <td>
            %if sample_values[field_index]:
                %if field['type'] == 'WorkflowField':
                    %if str(sample_values[field_index]) != 'none':
                        <% workflow = trans.sa_session.query( trans.app.model.StoredWorkflow ).get( int(sample_values[field_index]) ) %>
                        <a href="${h.url_for( controller='workflow', action='run', id=trans.security.encode_id(workflow.id) )}">${workflow.name}</a>
                    %endif
                %else:
                    ${sample_values[field_index]}
                %endif
            %else:
                <i>None</i>
            %endif
        </td>
    %endfor   
</%def>

<%def name="render_sample_form( index, sample_name, sample_values, fields_dict )">
    <td>
        ${sample_name}
    </td>
    %for field_index, field in fields_dict.items():
        <td>
            %if field['type'] == 'TextField':
                <input type="text" name="sample_${index}_field_${field_index}" value="${sample_values[field_index]}" size="7"/>
            %elif field['type'] == 'SelectField':
                <select name="sample_${index}_field_${field_index}" last_selected_value="2">
                    %for option_index, option in enumerate(field['selectlist']):
                        %if option == sample_values[field_index]:
                            <option value="${option}" selected>${option}</option>
                        %else:
                            <option value="${option}">${option}</option>
                        %endif
                    %endfor
                </select>
            %elif field['type'] == 'WorkflowField':
                <select name="sample_${index}_field_${field_index}">
                    %if str(sample_values[field_index]) == 'none':
                        <option value="none" selected>Select one</option>
                    %else:
                        <option value="none">Select one</option>
                    %endif
                    %for option_index, option in enumerate(request.user.stored_workflows):
                        %if not option.deleted:
                            %if str(option.id) == str(sample_values[field_index]):
                                <option value="${option.id}" selected>${option.name}</option>
                            %else:
                                <option value="${option.id}">${option.name}</option>
                            %endif
                        %endif
                    %endfor
                </select>
            %elif field['type'] == 'CheckboxField':
                <input type="checkbox" name="sample_${index}_field_${field_index}" value="Yes"/>
            %endif
            <div class="toolParamHelp" style="clear: both;">
                <i>${'('+field['required']+')' }</i>
            </div>
        </td>
    %endfor   
</%def>










