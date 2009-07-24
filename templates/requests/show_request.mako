<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif


<div class="grid-header">
    <h2>Sequencing Request "${request.name}"</h2>
</div>


<ul class="manage-table-actions">
    %if not request.submitted and request.samples:
        <li>
            <a class="action-button" confirm="More samples cannot be added to this request once it is submitted. Click OK to submit." href="${h.url_for( controller='requests', action='submit_request', id=request.id)}">
            <span>Submit request</span></a>
        </li>
    %endif
    <li>
        <a class="action-button"  href="${h.url_for( controller='requests', action='list')}">
        <span>Browse requests</span></a>
    </li>
</ul>



<%def name="render_sample_form( index, sample_name, sample_values )">
    <td>
        <input type="text" name=sample_${index}_name value="${sample_name}" size="15"/>
        <div class="toolParamHelp" style="clear: both;">
            <i>${' (required)' }</i>
        </div>
    </td>
    <td>
    </td>
    %for field_index, field in enumerate(request.type.sample_form.fields):
        <td>
            <input type="text" name=sample_${index}_field_${field_index} value="${sample_values[field_index]}" size="15"/>
            <div class="toolParamHelp" style="clear: both;">
                <i>${'('+field['required']+')' }</i>
            </div>
        </td>
    %endfor   
</%def>

<%def name="render_sample( index, sample )">
    <td>
        ${sample.name}
    </td>
    <td>
        <a href="${h.url_for( controller='requests', action='show_events', sample_id=sample.id)}">${sample.current_state().name}</a>
    </td>
    %for field_index, field in enumerate(request.type.sample_form.fields):
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
    ##<div class="toolFormTitle">Request Details: '${request_details[0]['value']}'</div>
        <div class="form-row">
        <a href="${h.url_for( controller='requests', action='toggle_request_details', request_id=request.id )}">${details_state}</a>
        </div>
        %if details_state == "Hide request details":
            %for index, rd in enumerate(request_details):
                <div class="form-row">
                    <label>${rd['label']}</label>
                    %if not rd['value']:
                        <i>None</i>
                    %else:                      
                        %if rd['label'] == 'Library':
                            <a href="${h.url_for( controller='library', action='browse_library', id=request.library.id )}">${rd['value']}</a>
                        %else:
                            ${rd['value']}     
                        %endif
                    %endif
                </div>
                <div style="clear: both"></div>
            %endfor
        %endif
    </div>
</div>

<div class="toolForm">
    ##<div class="toolFormTitle">Samples (${len(request.samples)})</div>
    <form id="edit_form" name="edit_form" action="${h.url_for( controller='requests', action='show_request', request_id=request.id )}" method="post" >
        <div class="form-row">
            %if current_samples: 
                <table class="grid">
                    <thead>
                        <tr>
                            <th>No.</th>
                            <th>Sample Name</th>
                            <th>State</th>
                            %for field_index, field in enumerate(request.type.sample_form.fields):
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
                            <tr>
                                <td>${sample_index+1}</td>
                                %if sample_index in range(len(request.samples)):
                                    ${render_sample( sample_index, request.samples[sample_index] )}
                                %else:                                                            
                                    ${render_sample_form( sample_index, sample[0], sample[1])}
                                %endif
                                <td>
                                    %if not request.submitted:
                                        <a class="action-button" href="${h.url_for( controller='requests', action='delete_sample', request_id=request.id, sample_id=sample_index)}">
                                        <img src="${h.url_for('/static/images/delete_icon.png')}" />
                                        <span></span></a>
                                    %endif
                                </td>
                            </tr>                            
                        %endfor
                    </tbody>
                </table>
            %else:
                <label>There are no samples.</label>
            %endif
            
        </div>
        %if not request.submitted:
            <br/>
            <br/>
            <div class="form-row">            
                <ul class="manage-table-actions">
                    <li>
                        %if current_samples:
                            <a>Copy from sample no. </a>
                            ${sample_copy.get_html()}
                        %endif
                        <input type="submit" name="add_sample_button" value="Add New"/>
                        
                    </li>
                </ul>
            </div>
        %endif
        %if not request.submitted and (request.samples or current_samples): 
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="refresh" value="true" size="40"/>
                </div>
              <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="save_samples_button" value="Save"/>
            </div>
        %endif
    ##</div>
    </form>
</div>
