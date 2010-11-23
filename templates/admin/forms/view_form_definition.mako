<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, status )}
%endif

<%def name="render_grid( grid_index, grid_name, fields_dict )">
    %if grid_name:
        <div class="form-row">
            <label>${grid_name}</label>
        </div>
    %endif
    <div style="clear: both"></div>
    <table class="grid">
        <thead>
            <tr>
                %for index, field in fields_dict.items():
                    <th>${field[ 'label' ]}</th>
                %endfor
            </tr>
        <thead>
        <tbody>
            <tr>
                %for index, field in fields_dict.items():
                    <td>
                        ${field[ 'type' ]}: ${form_definition.field_as_html( field )}<br/>
                        <div class="toolParamHelp" style="clear: both;">
                            <i>${field[ 'helptext' ]}</i> - (${field[ 'required' ]})
                        </div>
                        %if field[ 'type' ] == 'SelectField':
                            <div class="toolParamHelp" style="clear: both;">
                                <label>Options:</label>
                                %for option in field[ 'selectlist' ]:
                                    ${option}
                                %endfor
                            </div>
                        %endif
                    </td>
                %endfor
            </tr>
        <tbody>
    </table>
</%def>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" href="${h.url_for( controller='forms', action='edit_form_definition', id=trans.security.encode_id( form_definition.current.id ) )}">Edit</a></li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Form definition "${form_definition.name}"  (${form_definition.type})</div>    
    %if form_definition.type == trans.app.model.FormDefinition.types.SAMPLE:
        %if form_definition.layout:
            %for grid_index, grid_name in enumerate( form_definition.layout ):
                ${render_grid( grid_index, grid_name, form_definition.grid_fields( grid_index ) )}
            %endfor
        %else:
            ${render_grid( 0, '', form_definition.grid_fields( None ) )}
        %endif
    %else:
        %for index, field in enumerate( form_definition.fields ):
            <div class="form-row">
                <label>${field[ 'label' ]}</label>
                ${field[ 'type' ]}: ${form_definition.field_as_html( field )}
                <div class="toolParamHelp" style="clear: both;">
                    <i>${field[ 'helptext' ]}</i> - (${field[ 'required' ]})
                </div>
                %if field[ 'type' ] == 'SelectField':
                    <div class="toolParamHelp" style="clear: both;">
                        <label>Options:</label>
                        %for option in field[ 'selectlist' ]:
                            ${option}
                        %endfor
                    </div>
                %endif
            </div>
            <div style="clear: both"></div>
        %endfor
    %endif
</div>
