<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif


<div class="grid-header">
    <h2>Sequencing Request "${request.name}"</h2>
</div>

<ul class="manage-table-actions">
    %if request.unsubmitted() and request.samples:
        <li>
            <a class="action-button" confirm="More samples cannot be added to this request once it is submitted. Click OK to submit." href="${h.url_for( controller='requests_admin', action='submit_request', id=request.id)}">
            <span>Submit request</span></a>
        </li>
    %endif
    %if request.submitted() and request.samples:
        <li>
            <a class="action-button" href="${h.url_for( controller='requests_admin', action='bar_codes', request_id=request.id)}">
            <span>Bar codes</span></a>
        </li>
    %endif
</ul>


<%def name="render_sample_form( index, sample_name, sample_values, grid_index, fields_dict )">
    %if grid_index == 0:
        <td>
            <input type="text" name=sample_${index}_name value="${sample_name}" size="10"/>
            <div class="toolParamHelp" style="clear: both;">
                <i>${' (required)' }</i>
            </div>
        </td>
        <td>
        </td>
    %else:
        <td>
            ${sample_name}
        </td>
    %endif
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
            %elif field['type'] == 'CheckboxField':
                <input type="checkbox" name="sample_${index}_field_${field_index}" value="Yes"/>
            %endif
            <div class="toolParamHelp" style="clear: both;">
                <i>${'('+field['required']+')' }</i>
            </div>
        </td>
    %endfor   
</%def>

<%def name="render_sample( index, sample, grid_index, fields_dict )">
    <td>
        ${sample.name}
    </td>
    %if grid_index == 0:
        <td>
            %if sample.request.unsubmitted():
                Unsubmitted
            %else:    
                <a href="${h.url_for( controller='requests_admin', action='show_events', sample_id=sample.id)}">${sample.current_state().name}</a>
            %endif    
        </td>
    %endif
    %for field_index, field in fields_dict.items():
        <td>
            %if sample.values.content[field_index]:
                ${sample.values.content[field_index]}
            %else:
                <i>None</i>
            %endif
        </td>
    %endfor   
</%def>

<div class="toolForm">
        <div class="form-row">
        <a href="${h.url_for( controller='requests_admin', action='toggle_request_details', request_id=request.id )}">${details_state}</a>
        </div>
        %if details_state == "Hide request details":
            %for index, rd in enumerate(request_details):
                <div class="form-row">
                    <label>${rd['label']}</label>
                    %if not rd['value']:
                        <i>None</i>
                    %else:                      
                        %if rd['label'] == 'Data library':
                            <a href="${h.url_for( controller='library_admin', action='browse_library', obj_id=request.library.id )}">${rd['value']}</a>
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
                        <a class="action-button"  href="${h.url_for( controller='requests_admin', action='edit', show=True, request_id=request.id)}">
                        <span>Edit request details</span></a>
                    </li>
                </ul>
            </div>
        %endif
    </div>
</div>

<%def name="render_grid( grid_index, grid_name, fields_dict )">
    %if grid_name:
        <div class="toolFormTitle">${grid_name}</div>
    %endif
    <div style="clear: both"></div>
    <table class="grid">
        <thead>
            <tr>
                <th>No.</th>
                <th>Sample Name</th>
                %if grid_index == 0:
                    <th>State</th>
                %endif
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
            request.refresh()
            %>
            %for sample_index, sample in enumerate(current_samples):
                %if edit_mode:
                    <tr>
                        <td>${sample_index+1}</td>
                        ${render_sample_form( sample_index, sample[0], sample[1], grid_index, fields_dict)}
                        <td>
                            %if request.unsubmitted() and grid_index == 0:
                                <a class="action-button" href="${h.url_for( controller='requests', action='delete_sample', request_id=request.id, sample_id=sample_index)}">
                                <img src="${h.url_for('/static/images/delete_icon.png')}" />
                                <span></span></a>
                            %endif
                        </td>
                    </tr>      
                %else:
                    <tr>
                        <td>${sample_index+1}</td>
                        %if sample_index in range(len(request.samples)):
                            ${render_sample( sample_index, request.samples[sample_index], grid_index, fields_dict )}
                        %else:                                                            
                            ${render_sample_form( sample_index, sample[0], sample[1], grid_index, fields_dict)}
                        %endif
                        <td>
                            %if request.unsubmitted() and grid_index == 0:
                                <a class="action-button" href="${h.url_for( controller='requests', action='delete_sample', request_id=request.id, sample_id=sample_index)}">
                                <img src="${h.url_for('/static/images/delete_icon.png')}" />
                                <span></span></a>
                            %endif
                        </td>
                    </tr>  
                %endif
            %endfor
        </tbody>
    </table>
</%def>

<div class="toolForm">
    ##<div class="toolFormTitle">Samples (${len(request.samples)})</div>
    <form id="edit_form" name="edit_form" action="${h.url_for( controller='requests_admin', action='show_request' )}" enctype="multipart/form-data" method="post" >
        <div class="form-row">
            %if current_samples: 
                %if not request.type.sample_form.layout:
                    ${render_grid( 0, "", request.type.sample_form.fields_of_grid( None ) )}
                %else:
                    %for grid_index, grid_name in enumerate(request.type.sample_form.layout):
                        ${render_grid( grid_index, grid_name, request.type.sample_form.fields_of_grid( grid_name ) )}
                    %endfor
                %endif
            %else:
                <label>There are no samples.</label>
            %endif
        </div>
        %if not edit_mode:
            <table class="grid">
                <tbody>
                    <tr>
                        <div class="form-row">
                            <td>
                                %if current_samples and not request.complete():                        
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
            <div class="form-row">
                %if edit_mode:   
                    <input type="submit" name="save_samples_button" value="Save"/>
                    <input type="submit" name="cancel_changes_button" value="Cancel"/>
                %elif request.unsubmitted():
                    <input type="submit" name="save_samples_button" value="Save"/>
                %endif
            </div>
        %endif
        <input type="hidden" name="request_id" value="${request.id}" />
    </form>
</div>
