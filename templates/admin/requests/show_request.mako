<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/requests/sample_state.mako" import="render_sample_state" />
<%namespace file="/requests/sample_datasets.mako" import="render_sample_datasets" />

%if msg:
    ${render_msg( msg, messagetype )}
%endif

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
            url: "${h.url_for( controller='requests_admin', action='sample_state_updates' )}",
            dataType: "json",
            data: { ids: ids.join( "," ), states: states.join( "," ) },
            success : function ( data ) {
                $.each( data, function( id, val ) {
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


%if request.rejected():
    ${render_msg( "Reason for rejection: "+request.last_comment(), "warning" )}
%endif

<div class="grid-header">
    <h2>Sequencing Request "${request.name}"</h2>
</div>

<ul class="manage-table-actions">

    %if request.unsubmitted() and request.samples:
        <li>
            <a class="action-button" confirm="More samples cannot be added to this request once it is submitted. Click OK to submit." href="${h.url_for( controller='requests_admin', action='list', operation='Submit', id=trans.security.encode_id(request.id) )}">
            <span>Submit request</span></a>
        </li>
    %endif
    %if request.submitted():
        <li>
            <a class="action-button" href="${h.url_for( controller='requests_admin', action='list', operation='Reject', id=trans.security.encode_id(request.id))}">
            <span>Reject request</span></a>
        </li>
    %endif
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_admin', action='list', operation='events', id=trans.security.encode_id(request.id) )}">
        <span>History</span></a>
    </li>


</ul>

<%def name="show_basic_info_form( sample_index, sample, info )">
    <td>
        <input type="text" name=sample_${sample_index}_name value="${info['name']}" size="10"/>
        <div class="toolParamHelp" style="clear: both;">
            <i>${' (required)' }</i>
        </div>
    </td>
    %if sample:
        %if sample.request.unsubmitted():
            <td></td>
        %else:
            <td><input type="text" name=sample_${sample_index}_barcode value="${info['barcode']}" size="10"/></td>
        %endif
    %else:
        <td></td>
    %endif
    %if sample:
        %if sample.request.unsubmitted():
            <td>Unsubmitted</td>
        %else:
            <td><a href="${h.url_for( controller='requests_admin', action='show_events', sample_id=sample.id)}">${sample.current_state().name}</a></td>
        %endif    
    %else:
        <td></td>
    %endif
    <td>${info['lib_widget'].get_html()}</td>
    <td>${info['folder_widget'].get_html()}</td>
    %if request.submitted() or request.complete(): 
        %if sample:
            <td><a href="${h.url_for( controller='requests_admin', action='show_datatx_page', sample_id=trans.security.encode_id(sample.id) )}">${len(sample.dataset_files)}</a></td> 
        %else:
            <td><a href="${h.url_for( controller='requests_admin', action='show_datatx_page', sample_id=trans.security.encode_id(sample.id) )}">Add</a></td>
        %endif 
    %endif 
</%def>

## This function displays the "Basic Information" grid
<%def name="render_basic_info_grid()">
    <h4>Sample Information</h4>
    <table class="grid">
        <thead>
            <tr>
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
                            <td>${info['name']}</td>
                            <td>${info['barcode']}</td>
                            %if sample.request.unsubmitted():
                                <td>Unsubmitted</td>
                            %else:
                                <td id="sampleState-${sample.id}">${render_sample_state( sample )}</td>
                            %endif
                                
##                            <td>
##                                %if sample:
##                                    %if sample.request.unsubmitted():
##                                        Unsubmitted
##                                    %else:
##                                        <a href="${h.url_for( controller='requests_admin', action='show_events', sample_id=sample.id)}">${sample.current_state().name}</a>
##                                    %endif
##                                %endif
##                            </td>
                            %if info['library']:
                                <td><a href="${h.url_for( controller='library_common', action='browse_library', cntrller='library', id=trans.security.encode_id( info['library'].id ) )}">${info['library'].name}</a></td>
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
                                    ${render_sample_datasets( sample )}
##                                    <a href="${h.url_for( controller='requests_admin', action='show_datatx_page', sample_id=trans.security.encode_id(sample.id) )}">${len(sample.dataset_files)}</a>
                                </td>
                            %endif
                            
                            
                        %else:                                                            
                            ${show_basic_info_form( sample_index, sample, info )}
                        %endif
                        %if request.unsubmitted() or request.rejected(): 
                            <td>
                                %if sample:
                                    %if sample.request.unsubmitted():
                                        <a class="action-button" href="${h.url_for( controller='requests_admin', action='delete_sample', request_id=request.id, sample_id=sample_index )}">
                                        <img src="${h.url_for('/static/images/delete_icon.png')}" />
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

<%def name="render_sample( index, sample_name, sample_values, fields_dict )">
    <td>
        ${sample_name}
    </td>
    %for field_index, field in fields_dict.items():
        <td>
            %if sample_values[field_index]:
                %if field['type'] == 'WorkflowField':
                    <% workflow = trans.sa_session.query( trans.app.model.StoredWorkflow ).get( int(sample_values[field_index]) ) %>
                    <a href="${h.url_for( controller='workflow', action='run', id=trans.security.encode_id(workflow.id) )}">${workflow.name}</a>
                %else:
                    ${sample_values[field_index]}
                %endif
            %else:
                <i>None</i>
            %endif
        </td>
    %endfor   
</%def>

<div class="toolForm">
    <div class="form-row">
        <div class="msg_list">
            <h4 class="msg_head"><u>Request Information</u></h4>
            <div class="msg_body">
                %for index, rd in enumerate(request_details):
                    <div class="form-row">
                        <label>${rd['label']}</label>
                        %if not rd['value']:
                            <i>None</i>
                        %else:                      
                            %if rd['label'] == 'State':
                                <a href="${h.url_for( controller='requests_admin', action='list', operation='events', id=trans.security.encode_id(request.id) )}">${rd['value']}</a>
                            %else:
                                ${rd['value']}     
                            %endif
                        %endif
                    </div>
                    <div style="clear: both"></div>
                %endfor
                <div class="form-row">
                <ul class="manage-table-actions">
                    <li>
                        <a class="action-button"  href="${h.url_for( controller='requests_admin', action='list', operation='Edit', id=trans.security.encode_id(request.id))}">
                        <span>Edit request details</span></a>
                    </li>
                </ul>
                </div>
            </div>
        </div>
    </div>
</div>

<br/>


<%def name="render_grid( grid_index, grid_name, fields_dict )">
    <br/>
    <div class="msg_list">
    %if grid_name:
        <h4 class="msg_head"><u>${grid_name}</u></h4>
    %else:
        <h4>Grid ${grid_index}</h4>
    %endif
    %if edit_mode == 'False' or len(current_samples) <= len(request.samples):
        <div class="msg_body">
    %else:
        <div class="msg_body2">
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

<div class="toolForm">
    ##<div class="toolFormTitle">Samples (${len(request.samples)})</div>
    <form id="show_request" name="show_request" action="${h.url_for( controller='requests_admin', action='show_request', edit_mode=edit_mode )}" enctype="multipart/form-data" method="post" >
        <div class="form-row">
            %if current_samples:
                ## first render the basic info grid 
                ${render_basic_info_grid()}
                ## then render the other grid(s)
                <% trans.sa_session.refresh( request.type.sample_form ) %>
                %for grid_index, grid_name in enumerate(request.type.sample_form.layout):
                    ${render_grid( grid_index, grid_name, request.type.sample_form.fields_of_grid( grid_index ) )}
                    <br/>
                %endfor
            %else:
                <label>There are no samples.</label>
            %endif
        </div>
        
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
                            <td>
                                %if current_samples:                        
                                    <input type="submit" name="edit_samples_button" value="Edit samples"/>
                                %endif
                            </td>
                            %if request.unsubmitted():
                                <td>
                                    <label>Import from csv file</label>           
                                    <input type="file" name="file_data" />
                                    <input type="submit" name="import_samples_button" value="Import samples"/>
                                </td>
                                <td>
                                    %if current_samples:
                                        <label>Copy from sample</label>
                                        ${sample_copy.get_html()}
                                    %endif
                                    <input type="submit" name="add_sample_button" value="Add New"/>
                                </td>
                            %endif
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
            %elif request.unsubmitted():
                <div class="form-row">
                    <input type="submit" name="save_samples_button" value="Save"/>
                </div>
            %endif
            
        %endif
        <input type="hidden" name="request_id" value="${request.id}" />
    </form>
</div>
