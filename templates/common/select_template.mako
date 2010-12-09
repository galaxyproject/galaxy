<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%
    in_library = form_type == trans.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE
    in_sample_tracking = form_type == trans.model.FormDefinition.types.RUN_DETAILS_TEMPLATE
    if in_library:
        # If rendering for a library folder or dataset, inheritance is set by the user, while
        # rendering for a RequestType, the template is always available to samples.
        from galaxy.web.form_builder import CheckboxField
        inheritable_check_box = CheckboxField( 'inheritable' )
%>

<br/><br/>
<ul class="manage-table-actions">
    %if in_library:
        <li><a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=library_id, use_panels=use_panels, show_deleted=show_deleted )}"><span>Browse the data library</span></a></li>
    %elif in_sample_tracking:
        <li><a class="action-button" href="${h.url_for( controller='request_type', action='view_request_type', id=request_type_id )}"><span>Browse the configuration</span></a></li>
    %endif
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Select a template for the ${item_desc} '${item_name}'</div>
    <div class="toolFormBody">
        %if form_type == trans.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE:
            <form id="select_template" name="select_template" action="${h.url_for( controller='library_common', action='add_template', cntrller=cntrller, item_type=item_type, form_type=trans.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, use_panels=use_panels, show_deleted=show_deleted )}" method="post" >
        %elif form_type == trans.model.FormDefinition.types.RUN_DETAILS_TEMPLATE:
            <form id="select_template" name="select_template" action="${h.url_for( controller='request_type', action='add_template', cntrller=cntrller, item_type=item_type, form_type=trans.model.FormDefinition.types.RUN_DETAILS_TEMPLATE, request_type_id=request_type_id, sample_id=sample_id )}" method="post">
        %endif
            <div class="form-row">
                <label>Template:</label>
                ${form_id_select_field.get_html()}
            </div>
            % if form_type == trans.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE and item_type in [ 'library', 'folder' ]:
                <div class="form-row">
                    %if inheritable_checked:
                        <% inheritable_check_box.checked = True %>
                    %endif
                    ${inheritable_check_box.get_html()}
                    <label for="inheritable" style="display:inline;">Inherit template to contained folders and datasets?</label>
                    <div class="toolParamHelp" style="clear: both;">
                        Check if you want this template to be used by other folders and datasets contained within this ${item_desc}
                    </div>
                </div>
            %endif
            <div class="form-row">
                <input type="submit" name="add_template_button" value="Use this template"/>
            </div>
        </form>
    </div>
</div>
<p/>
%if form_id_select_field.get_selected( return_label=True, return_value=True ) != ('Select one', 'none'):
    <div class="toolForm">
        <div class="toolFormTitle">Layout of selected template</div>
        <div class="toolFormBody">
            <div class="form-row">
                %for i, field in enumerate( widgets ):
                    <div class="form-row">
                        <label>${field[ 'label' ]}</label>
                        ${field[ 'widget' ].get_html( disabled=True )}
                        <div class="toolParamHelp" style="clear: both;">
                            ${field[ 'helptext' ]}
                        </div>
                        <div style="clear: both"></div>
                    </div>
                %endfor 
            </div>
        </div>
    </div>
%endif
