<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif


<div class="grid-header">
    <h2>Sequencing Request "${request.name}"</h2>
</div>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_admin', action='bar_codes', request_id=request.id)}">
        <span>Bar codes</span></a>
    </li>
</ul>

<%def name="render_sample( index, sample )">
    <td>
        ${sample.name}
    </td>
    <td>
        <a href="${h.url_for( controller='requests_admin', action='show_events', sample_id=sample.id)}">${sample.current_state().name}</a>
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
        <a href="${h.url_for( controller='requests_admin', action='toggle_request_details', request_id=request.id )}">${details_state}</a>
        </div>
        %if details_state == "Hide request details":
            %for index, rd in enumerate(request_details):
                <div class="form-row">
                    <label>${rd['label']}</label>
                    %if not rd['value']:
                        <i>None</i>
                    %else:                      
                        %if rd['label'] == 'Library':
                            <a href="${h.url_for( controller='admin', action='browse_library', id=request.library.id )}">${rd['value']}</a>
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
                        </tr>
                    <thead>
                    <tbody>
                        %for sample_index, sample in enumerate(current_samples):
                            <tr>
                                <td>${sample_index+1}</td>
                                ${render_sample( sample_index, request.samples[sample_index] )}
                            </tr>                            
                        %endfor
                    </tbody>
                </table>
            %else:
                <label>There are no samples.</label>
            %endif
            
        </div>
    ##</div>
    </form>
</div>
