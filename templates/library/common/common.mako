<%namespace file="/common/template_common.mako" import="render_template_field" />

<%def name="render_upload_form( cntrller, upload_option, action, library_id, folder_id, replace_dataset, file_formats, dbkeys, space_to_tab, link_data_only, widgets, roles_select_list, history, show_deleted )">
    <%
        import os, os.path
        from galaxy.web.form_builder import AddressField, CheckboxField, SelectField, TextArea, TextField, WorkflowField, WorkflowMappingField, HistoryField
    %>
    %if upload_option in [ 'upload_file', 'upload_directory', 'upload_paths' ]:
        <div class="toolForm" id="upload_library_dataset_tool_form">
            <%
                if upload_option == 'upload_directory':
                    tool_form_title = 'Upload a directory of files'
                elif upload_option == 'upload_paths':
                    tool_form_title = 'Upload files from filesystem paths'
                else:
                    tool_form_title = 'Upload files'
            %>
            <div class="toolFormTitle">${tool_form_title}</div>
            <div class="toolFormBody">
                <form name="upload_library_dataset" id="upload_library_dataset" action="${action}" enctype="multipart/form-data" method="post">
                    <input type="hidden" name="tool_id" value="upload1"/>
                    <input type="hidden" name="tool_state" value="None"/>
                    <input type="hidden" name="cntrller" value="${cntrller}"/>
                    <input type="hidden" name="library_id" value="${library_id}"/>
                    <input type="hidden" name="folder_id" value="${folder_id}"/>
                    <input type="hidden" name="show_deleted" value="${show_deleted}"/>
                    %if replace_dataset not in [ None, 'None' ]:
                        <input type="hidden" name="replace_id" value="${trans.security.encode_id( replace_dataset.id )}"/>
                        <div class="form-row">
                            You are currently selecting a new file to replace '<a href="${h.url_for( controller='library_common', action='ldda_info', cntrller=cntrller, library_id=library_id, folder_id=folder_id, id=trans.security.encode_id( replace_dataset.library_dataset_dataset_association.id ) )}">${replace_dataset.name}</a>'.
                            <div style="clear: both"></div>
                        </div>
                    %endif
                    %if replace_dataset in [ None, 'None' ]:
                        ## Don't allow multiple datasets to be uploaded when replacing a dataset with a new version
                        <div class="form-row">
                            <label>Upload option:</label>
                            <div class="form-row-input">
                                ${upload_option_select_list.get_html()}
                            </div>
                            <div class="toolParamHelp" style="clear: both;">
                                Choose upload option (file, directory, filesystem paths, current history).
                            </div>
                            <div style="clear: both"></div>
                        </div>
                    %else:
                        <input type="hidden" name="upload_option" value="upload_file"/>
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
                        <%
                            if link_data_only == 'No':
                                checked = ' checked'
                            else:
                                checked = ''
                            link_data_only_field = '<input type="checkbox" name="link_data_only" value="No"%s/>No' % checked
                        %>
                            <label>Copy data into Galaxy?</label>
                            <div class="form-row-input">
                                ${link_data_only_field}
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
                            <%
                                if space_to_tab == 'true':
                                    checked = ' checked'
                                else:
                                    checked = ''
                                if upload_option == 'upload_file':
                                    name = 'files_0|space_to_tab'
                                else:
                                    name = 'space_to_tab'
                                space2tab = '<input type="checkbox" name="%s" value="true"%s/>Yes' % ( name, checked )
                            %>
                            ${space2tab}
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
                            %if ldda_message:
                                <textarea name="ldda_message" rows="3" cols="35">${ldda_message}</textarea>
                            %else:
                                <textarea name="ldda_message" rows="3" cols="35"></textarea>
                            %endif
                        </div>
                        <div class="toolParamHelp" style="clear: both;">
                            This information will be displayed in the "Information" column for this dataset in the data library browser
                        </div>
                        <div style="clear: both"></div>
                    </div>
                    %if roles_select_list:
                        <div class="form-row">
                            <label>Restrict dataset access to specific roles:</label>
                            <div class="form-row-input">
                                ${roles_select_list.get_html()}
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
                        <input type="hidden" name="show_deleted" value="${show_deleted}"/>
                        <input type="hidden" name="upload_option" value="import_from_history"/>
                        <input type="hidden" name="ldda_message" value="${ldda_message}"/>
                        <%
                            role_ids_selected = ''
                            if roles_select_list:
                                selected = roles_select_list.get_selected( return_value=True, multi=True )
                                if selected:
                                    role_ids_selected = ','.join( selected )
                        %>
                        <input type="hidden" name="roles" value="${role_ids_selected}"/>
                        %if replace_dataset not in [ None, 'None' ]:
                            <input type="hidden" name="replace_id" value="${trans.security.encode_id( replace_dataset.id )}"/>
                            <div class="form-row">
                                You are currently selecting a new file to replace '<a href="${h.url_for( controller='library_common', action='ldda_info', cntrller=cntrller, library_id=library_id, folder_id=folder_id, id=trans.security.encode_id( replace_dataset.library_dataset_dataset_association.id ) )}">${replace_dataset.name}</a>'.
                                <div style="clear: both"></div>
                            </div>
                        %endif
                        ## Render hidden template fields so the contents will be associated with the dataset
                        %if widgets:
                            %for i, field in enumerate( widgets ):
                                ${render_template_field( field, render_as_hidden=True )}
                            %endfor 
                        %endif
                        %for hda in history.visible_datasets:
                            <% encoded_id = trans.security.encode_id( hda.id ) %>
                            <div class="form-row">
                                <input name="hda_ids" id="hist_${encoded_id}" value="${encoded_id}" type="checkbox"/>
                                <label for="hist_${encoded_id}" style="display: inline;font-weight:normal;">${hda.hid}: ${hda.name}</label>
                            </div>
                        %endfor
                        <div class="form-row">
                            <input type="submit" name="add_history_datasets_to_library_button" value="Import to library"/>
                        </div>
                    </form>
                %else:
                    <p>Your current history is empty</p>
                %endif
            </div>
        </div>
    %endif
</%def>

<%def name="render_actions_on_multiple_items()">
    <tfoot>
        <tr>
            <td colspan="5" style="padding-left: 42px;">
                For selected items:
                <select name="do_action" id="action_on_selected_items">
                    %if ( trans.user_is_admin() and cntrller=='library_admin' ):
                        <option value="manage_permissions">Edit permissions</option>
                        <option value="delete">Delete</option>
                    %elif cntrller in ['library', 'library_search']:
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
