<%def name="render_template_field( field, render_as_hidden=False )">
    <%
        from galaxy.web.form_builder import AddressField, CheckboxField, SelectField, TextArea, TextField, WorkflowField, WorkflowMappingField, HistoryField

        widget = field[ 'widget' ]
        has_contents = False
        label = field[ 'label' ]
        value = ''
        if isinstance( widget, TextArea ) and widget.value:
            has_contents = True
            if render_as_hidden:
                value = widget.value
            else:
                value = '<pre>%s</pre>' % widget.value
        elif isinstance( widget, TextField ) and widget.value:
            has_contents = True
            value = widget.value
        elif isinstance( widget, SelectField ) and widget.options:
            for option_label, option_value, selected in widget.options:
                if selected:
                    has_contents = True
                    value = option_value
        elif isinstance( widget, CheckboxField ) and widget.checked:
            has_contents = True
            if render_as_hidden:
                value = 'true'
            else:
                value = 'checked'
        elif isinstance( widget, WorkflowField ) and str( widget.value ).lower() not in [ 'none' ]:
            has_contents = True
            if render_as_hidden:
                value = widget.value
            else:
                workflow_user = widget.user
                if workflow_user:
                    for workflow in workflow_user.stored_workflows:
                        if not workflow.deleted and str( widget.value ) == str( workflow.id ):
                            value = workflow.name
                            break
                else:
                    # If we didn't find the selected workflow option above, we'll just print the value
                    value = widget.value
        elif isinstance( widget, WorkflowMappingField ) and str( widget.value ).lower() not in [ 'none' ]:
            has_contents = True
            if render_as_hidden:
                value = widget.value
            else:
                workflow_user = widget.user
                if workflow_user:
                    for workflow in workflow_user.stored_workflows:
                        if not workflow.deleted and str( widget.value ) == str( workflow.id ):
                            value = workflow.name
                            break
                else:
                    # If we didn't find the selected workflow option above, we'll just print the value
                    value = widget.value
        elif isinstance( widget, HistoryField ) and str( widget.value ).lower() not in [ 'none' ]:
            has_contents = True
            if render_as_hidden:
                value = widget.value
            else:
                history_user = widget.user
                if history_user:
                    for history in history_user.histories:
                        if not history.deleted and str( widget.value ) == str( history.id ):
                            value = history.name
                            break
                else:
                    # If we didn't find the selected workflow option above, we'll just print the value
                    value = widget.value
        elif isinstance( widget, AddressField ) and str( widget.value ).lower() not in [ 'none' ]:
            has_contents = True
            if render_as_hidden:
                value = widget.value
            else:
                address = trans.sa_session.query( trans.model.UserAddress ).get( int( widget.value ) )
                label = address.desc
                value = address.get_html()
    %>
    %if has_contents:
        % if render_as_hidden:
            <input type="hidden" name="${widget.name}" value="${value}"/>
        %else:
            <div class="form-row">
                <label>${label}</label>
                ${value}
                <div class="toolParamHelp" style="clear: both;">
                    ${field[ 'helptext' ]}
                </div>
                <div style="clear: both"></div>
            </div>
        %endif
    %endif
</%def>
            
<%def name="render_template_fields( cntrller, item_type, widgets, widget_fields_have_contents, request_type_id=None, sample_id=None, library_id=None, folder_id=None, ldda_id=None, info_association=None, inherited=False, editable=True )">
    <%  
        in_library = False
        in_sample_tracking = False

        if item_type == 'library':
            item = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
        elif item_type == 'folder':
            item = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( folder_id ) )
        elif item_type == 'ldda':
            item = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( ldda_id ) )
        elif item_type == 'request_type':
            item = trans.sa_session.query( trans.app.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
        elif item_type == 'sample':
            item = trans.sa_session.query( trans.app.model.Sample ).get( trans.security.decode_id( sample_id ) )

        if cntrller in [ 'library', 'library_admin' ]:
            in_library = True
            template_section_title = 'Other information'
            form_type = trans.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE
            if trans.user_is_admin() and cntrller == 'library_admin':
                can_modify = True
            elif cntrller == 'library':
                can_modify = trans.app.security_agent.can_modify_library_item( trans.get_current_user_roles(), item )
            else:
                can_modify = False
        elif cntrller in [ 'requests_admin', 'requests', 'request_type' ]:
            in_sample_tracking = True
            template_section_title = 'Run details'
            form_type = trans.model.FormDefinition.types.RUN_DETAILS_TEMPLATE
    %>
    %if ( in_sample_tracking and editable ) or ( in_library and editable and can_modify ):
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">
                <div class="menubutton popup" id="item-${item.id}-popup">${template_section_title}</div>
                <div popupmenu="item-${item.id}-popup">
                    %if in_library and info_association and inherited and can_modify:
                        ## "inherited" will be true only if the info_association is not associated with the current item,
                        ## which means that the currently display template has not yet been saved for the current item.
                        <a class="action-button" href="${h.url_for( controller='library_common', action='add_template', cntrller=cntrller, item_type=item_type, form_type=form_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}">Select a different template</a>
                    %elif in_library and info_association and not inherited and can_modify:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='edit_template', cntrller=cntrller, item_type=item_type, form_type=form_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}">Edit template</a>
                        <a class="action-button" href="${h.url_for( controller='library_common', action='delete_template', cntrller=cntrller, item_type=item_type, form_type=form_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}">Unuse template</a>
                        %if item_type not in [ 'ldda', 'library_dataset' ]:
                            %if info_association.inheritable:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='manage_template_inheritance', cntrller=cntrller, item_type=item_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}">Dis-inherit template</a>
                            %else:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='manage_template_inheritance', cntrller=cntrller, item_type=item_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}">Inherit template</a>
                            %endif
                        %endif
                    %elif in_sample_tracking:
                        <a class="action-button" href="${h.url_for( controller='request_type', action='add_template', cntrller=cntrller, item_type=item_type, form_type=form_type, request_type_id=request_type_id )}">Select a different template</a>
                        <a class="action-button" href="${h.url_for( controller='request_type', action='edit_template', cntrller=cntrller, item_type=item_type, form_type=form_type, request_type_id=request_type_id )}">Edit template</a>
                        <a class="action-button" href="${h.url_for( controller='request_type', action='delete_template', cntrller=cntrller, item_type=item_type, form_type=form_type, request_type_id=request_type_id )}">Unuse template</a>
                    %endif
                </div>
            </div>
            <div class="toolFormBody">
                %if in_library and inherited:
                    <div class="form-row">
                        <font color="red">
                            <b>
                                This is an inherited template and is not required to be used with this ${item_type}.  You can 
                                <a href="${h.url_for( controller='library_common', action='add_template', cntrller=cntrller, item_type=item_type, form_type=form_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}"><font color="red">Select a different template</font></a>
                                or fill in the desired fields and save this one.  This template will not be associated with this ${item_type} until you click the Save button.
                            </b>
                        </font>
                    </div>
                %endif
                %if in_library:
                    <form name="edit_info" id="edit_info" action="${h.url_for( controller='library_common', action='edit_template_info', cntrller=cntrller, item_type=item_type, form_type=form_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}" method="post">
                %elif in_sample_tracking:
                    <form name="edit_info" id="edit_info" action="${h.url_for( controller='request_type', action='edit_template_info', cntrller=cntrller, item_type=item_type, form_type=form_type, request_type_id=request_type_id, sample_id=sample_id )}" method="post">
                %endif
                    %for i, field in enumerate( widgets ):
                        <div class="form-row">
                            <label>${field[ 'label' ]}</label>
                            ${field[ 'widget' ].get_html()}
                            <div class="toolParamHelp" style="clear: both;">
                                ${field[ 'helptext' ]}
                            </div>
                            <div style="clear: both"></div>
                        </div>
                    %endfor 
                    <div class="form-row">
                        <input type="submit" name="edit_info_button" value="Save"/>
                    </div>
                </form>
            </div>
        </div>
        <p/>
    %elif widget_fields_have_contents:
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">Other information about ${item.name}</div>
            <div class="toolFormBody">
                %for i, field in enumerate( widgets ):
                    ${render_template_field( field )}
                %endfor
            </div>
        </div>
        <p/>
    %endif
</%def>
