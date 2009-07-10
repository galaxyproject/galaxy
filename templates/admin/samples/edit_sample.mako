<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Edit sample named: ${values.content['Name']}</div>
    <div class="toolFormBody">
        <form name="sample" action="${h.url_for( controller='sample', action='do', save_changes=True, sample_id=sample.id )}" method="post" >
            <div class="form-row">
                <label>
                    Library:
                </label>
                <select name="library_id">
                    %for library in libraries:
                        <option value="${library.id}">${library.name}</option>
                    %endfor
                </select>
            </div>
            %for i, field in enumerate(form.fields):
                <div class="form-row">
                    <label>${field['label']}</label>
                    %if field['type'] == 'TextField':
                        <input type="text" name="${field['label']}" value="${values.content[field['label']]}" size="40"/>
                    %elif field['type'] == 'TextArea':
                        <textarea name="${field['label']}" rows="3" cols="35">${values.content[field['label']]}</textarea>
                    %elif field['type'] == 'CheckBox':
                        %if values.content[field['label']] == "true":
                            <input type="checkbox" name="${field['label']}" value="true" checked>
                        %else:
                            <input type="checkbox" name="${field['label']}" value="true">
                        %endif
                    %elif field['type'] == 'SelectBox':
                        <select name="${field['label']}">
                            %for ft in field['selectlist']:
                                %if ft == values.content[field['label']]:
                                    <option value="${ft}" selected>${ft}</option>
                                %else:
                                    <option value="${ft}">${ft}</option>
                                %endif
                            %endfor
                        </select>
                    %endif
                    <div class="toolParamHelp" style="clear: both;">
                    ${field['helptext']}
                    </div>
                    <div style="clear: both"></div>
                </div>
            %endfor                    
            <div class="form-row">
                <div style="float: left; width: 250px; margin-right: 10px;">
                    <input type="hidden" name="new" value="submitted" size="40"/>
                </div>
              <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <input type="submit" name="create_library_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
<div class="toolForm">
    <div class="toolFormBody">
        <form name="event" action="${h.url_for( controller='admin', action='event', new=True, sample_id=sample.id)}" method="post" >
            <div class="form-row">
                <label>
                    Change sample state to:
                </label>
                <select name="state_id">
                    %for state in states:
                        <option value="${state.id}">${state.name}</option>
                    %endfor
                </select>
            </div>
            <div class="form-row">
                <input type="submit" name="add_event" value="Save"/>
            </div>
        </form>
    </div>
</div>