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
    %if form.desc:
        <div class="toolFormTitle">${form.name} - <i>${form.desc}</i>
            <a id="form-${form.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
            <div popupmenu="form-${form.id}-popup">
                <a class="action-button" href="${h.url_for( action='edit', form_id=form.id, show_form=True )}">Edit</a>
            </div>
        </div>
    %else:
        <div class="toolFormTitle">${form.name}
        <a id="form-${form.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
        <div popupmenu="form-${form.id}-popup">
            <a class="action-button" href="${h.url_for( action='edit', form_id=form.id, show_form=True )}">Edit</a>
        </div>
        </div>
    %endif
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
            %for index, field in enumerate(form.fields):
                <div class="form-row">
                    <label>${field['label']}</label>
                    %if field['helptext']:
                        <div class="toolParamHelp" style="clear: both;">
                            <i>${field['helptext']}</i>
                        </div>
                    %endif
                    <div>${field['required']}</div>
                    <i>Type: </i> ${field['type']}
                    %if field['type'] == 'SelectField':
                        <div>
                        <div><i>Options:</i></div>
                        %for option in field['selectlist']:
                            <div>${option}</div>
                        %endfor
                        </div>
                    %endif
                </div>
                <div style="clear: both"></div>
            %endfor
        %endif
    </form>
    </div>
</div>