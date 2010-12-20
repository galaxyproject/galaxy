<%def name="render_sequencer( sequencer, show_all='True' )">
    <div class="form-row">
        <label>Name:</label>
        %if show_all == 'True':
            ${sequencer.name}
        %else:
            <a href="${h.url_for( controller='sequencer', action='view_sequencer', id=trans.security.encode_id( sequencer.id ) )}">${sequencer.name}</a>
        %endif
        <div style="clear: both"></div>
    </div>
    %if show_all == 'True':
	    <div class="form-row">
	        <label>Description:</label>
	        ${sequencer.description}
	        <div style="clear: both"></div>
	    </div>
	    <div class="form-row">
	        <label>Version:</label>
	        ${sequencer.version}
	        <div style="clear: both"></div>
	    </div>
	    <div class="form-row">
	        <label>Create date:</label>
	        ${sequencer.create_time}
	        <div style="clear: both"></div>
	    </div>
	    <div class="form-row">
	        <label>Update date:</label>
	        ${sequencer.update_time}
	        <div style="clear: both"></div>
	    </div>
    %endif
    <div class="form-row">
        <label>Sequencer type:</label>
        %if trans.app.sequencer_types.all_sequencer_types.has_key( sequencer.sequencer_type_id ):
            ${trans.app.sequencer_types.all_sequencer_types[ sequencer.sequencer_type_id ].name}
        %else:
            ${'Error in loading sequencer type: %s' % sequencer.sequencer_type_id}
        %endif
        <div style="clear: both"></div>
    </div>

    %if sequencer.sequencer_type_id != 'none':
        %for field_index, field in enumerate( sequencer.form_definition.fields ):
            <% 
                field_value = sequencer.form_values.content[ field['name'] ]
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
            Sequencer information is not set, click the <b>Edit sequencer</b> button to set it.
        </div>
    %endif
    
</%def>
