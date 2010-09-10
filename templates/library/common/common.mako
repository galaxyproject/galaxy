<%def name="render_template_field( field )">
    <%
        from galaxy.web.form_builder import AddressField, CheckboxField, SelectField, TextArea, TextField, WorkflowField
        
        has_contents = False
        value = ''
        if isinstance( field[ 'widget' ], TextArea ) and field[ 'widget' ].value:
            has_contents = True
            label = field[ 'label' ]
            value = '<pre>%s</pre>' % field[ 'widget' ].value
        elif isinstance( field[ 'widget' ], TextField ) and field[ 'widget' ].value:
            has_contents = True
            label = field[ 'label' ]
            value = field[ 'widget' ].value
        elif isinstance( field[ 'widget' ], SelectField ) and field[ 'widget' ].options:
            for option_label, option_value, selected in field['widget'].options:
                if selected:
                    has_contents = True
                    label = field[ 'label' ]
                    value = option_value
        elif isinstance( field[ 'widget' ], CheckboxField ) and field[ 'widget' ].checked:
            has_contents = True
            label = field[ 'label' ]
            value = 'checked'
        elif isinstance( field[ 'widget' ], WorkflowField ) and str( field[ 'widget' ].value ).lower() not in [ 'none' ]:
            has_contents = True
            label = field[ 'label' ]
            widget = field[ 'widget' ]
            workflow_user = widget.user
            if workflow_user:
                for workflow in workflow_user.stored_workflows:
                    if not workflow.deleted and str( widget.value ) == str( workflow.id ):
                        value = workflow.name
                        break
            else:
                # If we didn't find the selected workflow option above, we'll just print the value
                value = field[ 'widget' ].value
        elif isinstance( field[ 'widget' ], AddressField ) and str( field[ 'widget' ].value ).lower() not in [ 'none' ]:
            has_contents = True
            widget = field[ 'widget' ]
            address = trans.sa_session.query( trans.model.UserAddress ).get( int( widget.value ) )
            label = address.desc
            value = address.get_html()
    %>
    %if has_contents:
        <div class="form-row">
            <label>${label}</label>
            ${value}
            <div class="toolParamHelp" style="clear: both;">
                ${field[ 'helptext' ]}
            </div>
            <div style="clear: both"></div>
        </div>
    %endif
</%def>
            
<%def name="render_template_fields( cntrller, item_type, library_id, widgets, widget_fields_have_contents, info_association, inherited, folder_id=None, ldda_id=None, editable=True )">
    <%  
        if item_type == 'library':
            item = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
        elif item_type == 'folder':
            item = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( folder_id ) )
        elif item_type == 'ldda':
            item = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( ldda_id ) )
        if trans.user_is_admin() and cntrller == 'library_admin':
            can_modify = True
        elif cntrller == 'library':
            can_modify = trans.app.security_agent.can_modify_library_item( trans.get_current_user_roles(), item )
        else:
            can_modify = False
    %>
    %if editable and can_modify:
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">Other information
                <a id="item-${item.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                <div popupmenu="item-${item.id}-popup">
                    %if info_association and inherited and can_modify:
                        ## "inherited" will be true only if the info_association is not associated with the current item,
                        ## which means that the currently display template has not yet been saved for the current item.
                        <a class="action-button" href="${h.url_for( controller='library_common', action='add_template', cntrller=cntrller, item_type=item_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}">Select a different template</a>
                    %elif info_association and not inherited and can_modify:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='edit_template', cntrller=cntrller, item_type=item_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}">Edit template</a>
                        <a class="action-button" href="${h.url_for( controller='library_common', action='delete_template', cntrller=cntrller, item_type=item_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}">Delete template</a>
                        %if item_type not in [ 'ldda', 'library_dataset' ]:
                            %if info_association.inheritable:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='manage_template_inheritance', cntrller=cntrller, item_type=item_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}">Dis-inherit template</a>
                            %else:
                                <a class="action-button" href="${h.url_for( controller='library_common', action='manage_template_inheritance', cntrller=cntrller, item_type=item_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}">Inherit template</a>
                            %endif
                        %endif
                    %endif
                </div>
            </div>
            <div class="toolFormBody">
                %if inherited:
                    <div class="form-row">
                        <font color="red">
                            <b>
                                This is an inherited template and is not required to be used with this ${item_type}.  You can 
                                <a href="${h.url_for( controller='library_common', action='add_template', cntrller=cntrller, item_type=item_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}"><font color="red">select a different template</font></a>
                                or fill in the desired fields and save this one.  This template will not be assocaiated with this ${item_type} until you click the Save button.
                            </b>
                        </font>
                    </div>
                %endif
                <form name="edit_info" id="edit_info" action="${h.url_for( controller='library_common', action='edit_template_info', cntrller=cntrller, item_type=item_type, library_id=library_id, folder_id=folder_id, ldda_id=ldda_id, show_deleted=show_deleted )}" method="post">
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

<%def name="render_upload_form( cntrller, upload_option, action, library_id, folder_id, replace_dataset, file_formats, dbkeys, widgets, roles, history, show_deleted )">
    <% import os, os.path %>
    %if upload_option in [ 'upload_file', 'upload_directory', 'upload_paths' ]:
        <div class="toolForm" id="upload_library_dataset_tool_form">
            %if upload_option == 'upload_directory':
                <div class="toolFormTitle">Upload a directory of files</div>
            %elif upload_option == 'upload_paths':
                <div class="toolFormTitle">Upload files from filesystem paths</div>
            %else:
                <div class="toolFormTitle">Upload files</div>
            %endif
            <div class="toolFormBody">
                <form name="upload_library_dataset" id="upload_library_dataset" action="${action}" enctype="multipart/form-data" method="post">
                    <input type="hidden" name="tool_id" value="upload1"/>
                    <input type="hidden" name="tool_state" value="None"/>
                    <input type="hidden" name="cntrller" value="${cntrller}"/>
                    <input type="hidden" name="library_id" value="${library_id}"/>
                    <input type="hidden" name="folder_id" value="${folder_id}"/>
                    <input type="hidden" name="upload_option" value="${upload_option}"/>
                    <input type="hidden" name="show_deleted" value="${show_deleted}"/>
                    %if replace_dataset not in [ None, 'None' ]:
                        <input type="hidden" name="replace_id" value="${trans.security.encode_id( replace_dataset.id )}"/>
                        <div class="form-row">
                            You are currently selecting a new file to replace '<a href="${h.url_for( controller='library_common', action='ldda_info', cntrller=cntrller, library_id=library_id, folder_id=folder_id, id=trans.security.encode_id( replace_dataset.library_dataset_dataset_association.id ) )}">${replace_dataset.name}</a>'.
                            <div style="clear: both"></div>
                        </div>
                    %endif
                    <div class="form-row">
                        <label>File Format:</label>
                        <div class="form-row-input">
                            <select name="file_type">
                                <option value="auto" selected>Auto-detect</option>
                                %for file_format in file_formats:
                                    <option value="${file_format}">${file_format}</option>
                                %endfor
                            </select>
                        </div>
                        <div style="clear: both"></div>
                    </div>
                    %if upload_option == 'upload_file':
                        <div class="form-row">
                            <input type="hidden" name="async_datasets" value="None"/>
                            <div style="clear: both"></div>
                        </div>
                        <div class="form-row">
                            <label>File:</label>
                            <div class="form-row-input">
                                <input type="file" name="files_0|file_data" galaxy-ajax-upload="true"/>
                            </div>
                            <div style="clear: both"></div>
                        </div>
                        <div class="form-row">
                            <label>URL/Text:</label>
                            <div class="form-row-input">
                                <textarea name="files_0|url_paste" rows="5" cols="35"></textarea>
                            </div>
                            <div class="toolParamHelp" style="clear: both;">
                                Specify a list of URLs (one per line) or paste the contents of a file.
                            </div>
                            <div style="clear: both"></div>
                        </div>
                    %elif upload_option == 'upload_directory':
                        <%
                            if ( trans.user_is_admin() and cntrller == 'library_admin' ):
                                import_dir = trans.app.config.library_import_dir
                            else:
                                # Directories of files from the Data Libraries view are restricted to a
                                # sub-directory named the same as the current user's email address
                                # contained within the configured setting for user_library_import_dir
                                import_dir = os.path.join( trans.app.config.user_library_import_dir, trans.user.email )
                        %>
                        <div class="form-row">
                            <%
                                # See if we have any contained sub-directories, if not the only option
                                # in the server_dir select list will be library_import_dir
                                contains_directories = False
                                for entry in os.listdir( import_dir ):
                                    if os.path.isdir( os.path.join( import_dir, entry ) ):
                                        contains_directories = True
                                        break
                            %>
                            <label>Server Directory</label>
                            <div class="form-row-input">
                                <select name="server_dir">
                                    %if contains_directories:
                                        <option>None</option>
                                        %for entry in os.listdir( import_dir ):
                                            ## Do not include entries that are not directories
                                            %if os.path.isdir( os.path.join( import_dir, entry ) ):
                                                <option>${entry}</option>
                                            %endif
                                        %endfor
                                    %else:
                                        %if ( trans.user_is_admin() and cntrller == 'library_admin' ):
                                            <option>${import_dir}</option>
                                        %else:
                                            <option>${trans.user.email}</option>
                                        %endif
                                    %endif
                                </select>
                            </div>
                            <div class="toolParamHelp" style="clear: both;">
                                %if contains_directories:
                                    Upload all files in a sub-directory of <strong>${import_dir}</strong> on the Galaxy server.
                                %else:
                                    Upload all files in <strong>${import_dir}</strong> on the Galaxy server.
                                %endif
                            </div>
                            <div style="clear: both"></div>
                        </div>
                    %elif upload_option == 'upload_paths':
                        <div class="form-row">
                            <label>Paths to upload</label>
                            <div class="form-row-input">
                                <textarea name="filesystem_paths" rows="10" cols="35"></textarea>
                            </div>
                            <div class="toolParamHelp" style="clear: both;">
                                Upload all files pasted in the box.  The (recursive) contents of any pasted directories will be added as well.
                            </div>
                        </div>
                        <div class="form-row">
                            <label>Preserve directory structure?</label>
                            <div class="form-row-input">
                                <input type="checkbox" name="dont_preserve_dirs" value="No"/>No
                            </div>
                            <div class="toolParamHelp" style="clear: both;">
                                If checked, all files in subdirectories on the filesystem will be placed at the top level of the folder, instead of into subfolders.
                            </div>
                        </div>
                    %endif
                    %if upload_option in ( 'upload_directory', 'upload_paths' ):
                        <div class="form-row">
                            <label>Copy data into Galaxy?</label>
                            <div class="form-row-input">
                                <input type="checkbox" name="link_data_only" value="No"/>No
                            </div>
                            <div class="toolParamHelp" style="clear: both;">
                                Normally data uploaded with this tool is copied into Galaxy's "files" directory
                                so any later changes to the data will not affect Galaxy.  However, this may not
                                be desired (especially for large NGS datasets), so use of this option will
                                force Galaxy to always read the data from its original path.
                                %if upload_option == 'upload_directory':
                                    Any symlinks encountered in the upload directory will be dereferenced once -
                                    that is, Galaxy will point directly to the file that is linked, but no other
                                    symlinks further down the line will be dereferenced.
                                %endif
                            </div>
                        </div>
                    %endif
                    <div class="form-row">
                        <label>
                            Convert spaces to tabs:
                        </label>
                        <div class="form-row-input">
                            ## The files grouping only makes sense in the upload_file context.
                            %if upload_option == 'upload_file':
                                <input type="checkbox" name="files_0|space_to_tab" value="Yes"/>Yes
                            %else:
                                <input type="checkbox" name="space_to_tab" value="Yes"/>Yes
                            %endif
                        </div>
                        <div class="toolParamHelp" style="clear: both;">
                            Use this option if you are entering intervals by hand.
                        </div>
                    </div>
                    <div style="clear: both"></div>
                    <div class="form-row">
                        <label>Genome:</label>
                        <div class="form-row-input">
                            <select name="dbkey" last_selected_value="?">
                                %for dbkey in dbkeys:
                                    %if dbkey[1] == last_used_build:
                                        <option value="${dbkey[1]}" selected>${dbkey[0]}</option>
                                    %else:
                                        <option value="${dbkey[1]}">${dbkey[0]}</option>
                                    %endif
                                %endfor
                            </select>
                        </div>
                        <div style="clear: both"></div>
                    </div>
                    <div class="form-row">
                        <label>Message:</label>
                        <div class="form-row-input">
                            <textarea name="message" rows="3" cols="35"></textarea>
                        </div>
                        <div class="toolParamHelp" style="clear: both;">
                            This information will be displayed in the "Information" column for this dataset in the data library browser
                        </div>
                        <div style="clear: both"></div>
                    </div>
                    %if roles:
                        <div class="form-row">
                            <label>Restrict dataset access to specific roles:</label>
                            <div class="form-row-input">
                                <select name="roles" multiple="true" size="5">
                                    %for role in roles:
                                        <option value="${role.id}">${role.name}</option>
                                    %endfor
                                </select>
                            </div>
                            <div class="toolParamHelp" style="clear: both;">
                                Multi-select list - hold the appropriate key while clicking to select multiple roles.  More restrictions can be applied after the upload is complete.  Selecting no roles makes a dataset public.
                            </div>
                        </div>
                        <div style="clear: both"></div>
                    %endif
                    %if widgets:
                        %for i, field in enumerate( widgets ):
                            <div class="form-row">
                                <label>${field[ 'label' ]}</label>
                                <div class="form-row-input">
                                    ${field[ 'widget' ].get_html()}
                                </div>
                                <div class="toolParamHelp" style="clear: both;">
                                    %if field[ 'helptext' ]:
                                        ${field[ 'helptext' ]}<br/>
                                    %endif
                                    *Inherited template field
                                </div>
                                <div style="clear: both"></div>
                            </div>
                        %endfor 
                    %endif
                    <div class="form-row">
                        <input type="submit" class="primary-button" name="runtool_btn" value="Upload to library"/>
                    </div>
                </form>
            </div>
        </div>
        ## Script to replace dbkey select with select+search.
        <script type="text/javascript">
            // Replace dbkey select with search+select.
            jQuery(document).ready( function() {
                replace_big_select_inputs();
            });
        </script>
    %elif upload_option == 'import_from_history':
        <div class="toolForm">
            <div class="toolFormTitle">Active datasets in your current history (${history.name})</div>
            <div class="toolFormBody">
                %if history and history.active_datasets:
                    <form name="add_history_datasets_to_library" action="${h.url_for( controller='library_common', action='add_history_datasets_to_library', cntrller=cntrller, library_id=library_id )}" enctype="multipart/form-data" method="post">
                        <input type="hidden" name="folder_id" value="${folder_id}"/>
                        <input type="hidden" name="upload_option" value="${upload_option}"/>
                        %if replace_dataset not in [ None, 'None' ]:
                            <input type="hidden" name="replace_id" value="${trans.security.encode_id( replace_dataset.id )}"/>
                            <div class="form-row">
                                You are currently selecting a new file to replace '<a href="${h.url_for( controller='library_common', action='ldda_info', cntrller=cntrller, library_id=library_id, folder_id=folder_id, id=trans.security.encode_id( replace_dataset.library_dataset_dataset_association.id ) )}">${replace_dataset.name}</a>'.
                                <div style="clear: both"></div>
                            </div>
                        %endif
                        %for hda in history.active_datasets:
                            <div class="form-row">
                                <input name="hda_ids" value="${trans.security.encode_id( hda.id )}" type="checkbox"/>${hda.hid}: ${hda.name}
                            </div>
                        %endfor
                        <div class="form-row">
                            <input type="submit" name="add_history_datasets_to_library_button" value="Import to library"/>
                        </div>
                    </form>
                %else:
                    <p/>
                    Your current history is empty
                    <p/>
                %endif
            </div>
        </div>
    %endif
</%def>

<%def name="render_actions_on_multiple_items()">
    <tfoot>
        <tr>
            <td colspan="4" style="padding-left: 42px;">
                For selected items:
                <select name="do_action" id="action_on_selected_items">
                    %if ( trans.user_is_admin() and cntrller=='library_admin' ):
                        <option value="manage_permissions">Edit permissions</option>
                        <option value="delete">Delete</option>
                    %elif cntrller=='library':
                        %if default_action == 'add':
                            <option value="add" selected>Import into your current history</option>
                        %else:
                            <option value="add">Import into your current history</option>
                        %endif
                        %if default_action == 'manage_permissions':
                            <option value="manage_permissions" selected>Edit permissions</option>
                            # This condition should not contain an else clause because the user is not authorized
                            # to manage dataset permissions unless the default action is 'manage_permissions'
                        %endif
                        %if 'gz' in comptypes:
                            <option value="tgz"
                            %if default_action == 'download':
                                selected
                            %endif>
                            >Download  as a .tar.gz file</option>
                        %endif
                        %if 'bz2' in comptypes:
                            <option value="tbz">Download as a .tar.bz2 file</option>
                        %endif
                        %if 'zip' in comptypes:
                            <option value="zip">Download as a .zip file</option>
                        %endif
                        %if 'ngxzip' in comptypes:
                            ## We can safely have two default selected items since ngxzip, if present, will always be the only available type.
                            <option value="ngxzip"
                            %if default_action == 'download':
                                selected
                            %endif>
                            >Download as a .zip file</option>
                        %endif
                    %endif
                </select>
                <input type="submit" class="primary-button" name="action_on_datasets_button" id="action_on_datasets_button" value="Go"/>
            </td>
        </tr>
    </tfoot>
</%def>
