<%def name="render_external_service( external_service )">
    <div class="toolForm">
        <div class="toolFormTitle">External service</div>
        <div class="form-row">
            <label>Name:</label>
            ${external_service.name}
            ##<a href="${h.url_for( controller='external_service', action='view_external_service', id=trans.security.encode_id( external_service.id ) )}">${external_service.name}</a>
            <div style="clear: both"></div>
        </div>
	    <div class="form-row">
	        <label>Description:</label>
	        ${external_service.description}
	        <div style="clear: both"></div>
	    </div>
	    <div class="form-row">
	        <label>Version:</label>
	        ${external_service.version}
	        <div style="clear: both"></div>
	    </div>
        <div class="form-row">
            <label>External service type:</label>
            %if trans.app.external_service_types.all_external_service_types.has_key( external_service.external_service_type_id ):
                ${trans.app.external_service_types.all_external_service_types[ external_service.external_service_type_id ].name}
            %else:
                ${'Error loading external_service type: %s' % external_service.external_service_type_id}
            %endif
            <div style="clear: both"></div>
        </div>
        %if external_service.external_service_type_id != 'none':
            %for field_index, field in enumerate( external_service.form_definition.fields ):
                <% 
                    field_value = external_service.form_values.content.get( field['name'], '' )
                    if field[ 'type' ] == 'PasswordField':
                        field_value = '*' * len( field_value )
                %>
                <div class="form-row">
                    <label>${field[ 'label' ]}:</label>
                    ${field_value}
                </div>
            %endfor
        %else:
            <div class="form-row">
                External service information is not set, click the <b>Edit external service</b> button to set it.
            </div>
        %endif
    </div>
</%def>
