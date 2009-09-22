<%def name="render_upload_form( controller, upload_option, library_id, folder_id, replace_dataset, file_formats, dbkeys, roles, history )">
    <% import os, os.path %>
    %if upload_option in [ 'upload_file', 'upload_directory' ]:
        <div class="toolForm" id="upload_library_dataset">
            %if upload_option == 'upload_file':
                <div class="toolFormTitle">Upload files</div>
            %else:
                <div class="toolFormTitle">Upload a directory of files</div>
            %endif
            <div class="toolFormBody">
                <form name="upload_library_dataset" action="${h.url_for( controller=controller, action='library_dataset_dataset_association', library_id=library_id )}" enctype="multipart/form-data" method="post">
                    <input type="hidden" name="tool_id" value="upload_library_dataset"/>
                    <input type="hidden" name="tool_state" value="None"/>
                    <input type="hidden" name="folder_id" value="${folder_id}"/>
                    <input type="hidden" name="upload_option" value="${upload_option}"/>
                    %if replace_dataset not in [ None, 'None' ]:
                        <input type="hidden" name="replace_id" value="${replace_dataset.id}"/>
                        <div class="form-row">
                            You are currently selecting a new file to replace '<a href="${h.url_for( controller=controller, action='library_dataset_dataset_association', library_id=library_id, folder_id=folder_id, id=replace_dataset.library_dataset_dataset_association.id )}">${replace_dataset.name}</a>'.
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
                            if controller == 'library_admin':
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
                                        %if controller == 'library_admin':
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
                    %endif
                    <div class="form-row">
                        <label>
                            Convert spaces to tabs:
                        </label>
                        <div class="form-row-input">
                            <input type="checkbox" name="files_0|space_to_tab" value="Yes"/>Yes
                        </div>
                    </div>
                    <div class="toolParamHelp" style="clear: both;">
                        Use this option if you are entering intervals by hand.
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
                                    ${field[ 'helptext' ]}
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
    %elif upload_option == 'import_from_history':
        <div class="toolForm">
            <div class="toolFormTitle">Active datasets in your current history (${history.name})</div>
            <div class="toolFormBody">
                %if history and history.active_datasets:
                    <form name="add_history_datasets_to_library" action="${h.url_for( controller=controller, action='add_history_datasets_to_library', library_id=library_id )}" enctype="multipart/form-data" method="post">
                        <input type="hidden" name="folder_id" value="${folder_id}"/>
                        <input type="hidden" name="upload_option" value="${upload_option}"/>
                        %if replace_dataset not in [ None, 'None' ]:
                            <input type="hidden" name="replace_id" value="${replace_dataset.id}"/>
                            <div class="form-row">
                                You are currently selecting a new file to replace '<a href="${h.url_for( controller=controller, action='library_dataset_dataset_association', library_id=library_id, folder_id=folder_id, id=replace_dataset.library_dataset_dataset_association.id )}">${replace_dataset.name}</a>'.
                                <div style="clear: both"></div>
                            </div>
                        %endif
                        %for hda in history.active_datasets:
                            <div class="form-row">
                                <input name="hda_ids" value="${hda.id}" type="checkbox"/>${hda.hid}: ${hda.name}
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
