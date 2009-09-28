<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />


%if msg:
    ${render_msg( msg, messagetype )}
%endif

<%def name="render_grid( grid_index, grid_name, fields_dict )">
    %if grid_name:
        <div class="toolFormTitle">${grid_name}</div>
    %endif
    <div style="clear: both"></div>
    <table class="grid">
        <thead>
            <tr>
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
            <tr>
                %for index, field in fields_dict.items():
                    <td>
                        <div>${field['required']}</div>
##                        <div>${field['type']}</div>
                    </td>
                %endfor
                <th></th>
            </tr>
                %for index, field in fields_dict.items():
                    <td>
##                        <div>${field['required']}</div>
                        <div><i>Type:</i></div>
                        <div>${field['type']}</div>
                    </td>
                %endfor
                <th></th>
            </tr>
            <tr>
                %for index, field in fields_dict.items():
                    <td>
                        %if field['type'] == 'SelectField':
                            <div><i>Options:</i></div>
                            %for option in field['selectlist']:
                                <div>${option}</div>
                            %endfor
                        %endif
                    </td>
                %endfor
                <th></th>
            </tr>
        <tbody>
    </table>
</%def>

<div class="toolForm">
    <div class="toolFormTitle">${form.name} - <i>${form.desc}</i></div>
    <form name="library" action="${h.url_for( controller='forms', action='manage' )}" method="post" >
        %if form.type == trans.app.model.FormDefinition.types.SAMPLE:
            %if not len(form.layout):
                ${render_grid( 0, '', form.fields_of_grid( None ) )}
            %else:
                %for grid_index, grid_name in enumerate(form.layout):
                    ${render_grid( grid_index, grid_name, form.fields_of_grid( grid_name ) )}
                %endfor
            %endif
        %else:
            <table class = "grid">
                <tbody>
                    %for index, field in enumerate(form.fields):
                        <tr>
                            <td>
                                <div class="form-row">
                                    <label>${1+index}. Label</label>
                                    <a>${field['label']}</a>
                                    %if field['type'] == 'SelectField':
                                        <a id="${field['label']}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                                        %for option in field['selectlist']:
                                            <div popupmenu="${field['label']}-type-popup">
                                                <a class="action-button" href="" >${option}</a>
                                            </div>                                 
                                        %endfor
                                    %endif                                    
                                </div>
                            </td>
                            <td>
                                <div class="form-row">
                                    <label>Help text </label>
                                    %if not field['helptext']:
                                        <a><i>No helptext</i></a>
                                    %else:
                                        <a>${field['helptext']}</a>
                                    %endif
                                </div>
                            </td>                            
                            <td>
                                <div class="form-row">
                                    <label>Type:</label>
                                    <a>${field['type']}</a>
                                    %if field['type'] == 'SelectField':
                                        <a id="fieldtype-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                                        %for option in field['selectlist']:
                                            <div popupmenu="type-popup">
                                                <a class="action-button" href="" >${option}</a>
                                            </div>                                 
                                        %endfor
                                    %endif
                                </div>
                            </td>
                            <td>
                                <div class="form-row">
                                    <label>Required?</label>
                                    <a>${field['required']}</a>
                                </div>
                            </td>
                        </tr>       
                    %endfor
                </tbody>
            </table>
        %endif
    </form>
    </div>
</div>