
<%def name="common_javascripts(repository)">
    <script type="text/javascript">
        $(function(){
            $("#tree").ajaxComplete(function(event, XMLHttpRequest, ajaxOptions) {
                _log("debug", "ajaxComplete: %o", this); // dom element listening
            });
            // --- Initialize sample trees
            $("#tree").dynatree({
                title: "${repository.name}",
                rootVisible: true,
                minExpandLevel: 0, // 1: root node is not collapsible
                persist: false,
                checkbox: true,
                selectMode: 3,
                onPostInit: function(isReloading, isError) {
                    //alert("reloading: "+isReloading+", error:"+isError);
                    logMsg("onPostInit(%o, %o) - %o", isReloading, isError, this);
                    // Re-fire onActivate, so the text is updated
                    this.reactivate();
                }, 
                fx: { height: "toggle", duration: 200 },
                // initAjax is hard to fake, so we pass the children as object array:
                initAjax: {url: "${h.url_for( controller='repository', action='open_folder' )}",
                           dataType: "json", 
                           data: { folder_path: "${repository.repo_path( trans.app )}" },
                },
                onLazyRead: function(dtnode){
                    dtnode.appendAjax({
                        url: "${h.url_for( controller='repository', action='open_folder' )}", 
                        dataType: "json",
                        data: { folder_path: dtnode.data.key },
                    });
                },
                onSelect: function(select, dtnode) {
                    // Display list of selected nodes
                    var selNodes = dtnode.tree.getSelectedNodes();
                    // convert to title/key array
                    var selKeys = $.map(selNodes, function(node) {
                        return node.data.key;
                    });
                    if (document.forms["select_files_to_delete"]) {
                        // The following is used only ~/templates/webapps/community/repository/browse_repository.mako.
                        document.select_files_to_delete.selected_files_to_delete.value = selKeys.join(",");
                    }
                    // The following is used only in ~/templates/webapps/community/repository/upload.mako.
                    if (document.forms["upload_form"]) {
                        document.upload_form.upload_point.value = selKeys.slice(-1);
                    }
                },
                onActivate: function(dtnode) {
                    var cell = $("#file_contents");
                    var selected_value;
                     if (dtnode.data.key == 'root') {
                        selected_value = "${repository.repo_path( trans.app )}/";
                    } else {
                        selected_value = dtnode.data.key;
                    };
                    if (selected_value.charAt(selected_value.length-1) != '/') {
                        // Make ajax call
                        $.ajax( {
                            type: "POST",
                            url: "${h.url_for( controller='repository', action='get_file_contents' )}",
                            dataType: "json",
                            data: { file_path: selected_value },
                            success : function ( data ) {
                                cell.html( '<label>'+data+'</label>' )
                            }
                        });
                    } else {
                        cell.html( '' );
                    };
                },
            });
        });
    </script>
</%def>

<%def name="container_javascripts()">
    <script type="text/javascript">
        var init_dependencies = function() {
            var storage_id = "library-expand-state-${trans.security.encode_id(10000)}";
            var restore_folder_state = function() {
                var state = $.jStorage.get(storage_id);
                if (state) {
                    for (var id in state) {
                        if (state[id] === true) {
                            var row = $("#" + id),
                                index = row.parent().children().index(row);
                            row.addClass("expanded").show();
                            row.siblings().filter("tr[parent='" + index + "']").show();
                        }
                    }
                }
            };
            var save_folder_state = function() {
                var state = {};
                $("tr.folderRow").each( function() {
                    var folder = $(this);
                    state[folder.attr("id")] = folder.hasClass("expanded");
                });
                $.jStorage.set(storage_id, state);
            };
            $(".container-table").each(function() {
                //var container_id = this.id.split( "-" )[0];
                //alert( container_id );
                var child_of_parent_cache = {};
                // Recursively fill in children and descendants of each row
                var process_row = function(q, parents) {
                    // Find my index
                    var parent = q.parent(),
                        this_level = child_of_parent_cache[parent] || (child_of_parent_cache[parent] = parent.children());
                    var index = this_level.index(q);
                    // Find my immediate children
                    var children = $(par_child_dict[index]);
                    // Recursively handle them
                    var descendants = children;
                    children.each( function() {
                        child_descendants = process_row( $(this), parents.add(q) );
                        descendants = descendants.add(child_descendants);
                    });
                    // Set up expand / hide link
                    var expand_fn = function() {
                        if ( q.hasClass("expanded") ) {
                            descendants.hide();
                            descendants.removeClass("expanded");
                            q.removeClass("expanded");
                        } else {
                            children.show();
                            q.addClass("expanded");
                        }
                        save_folder_state();
                    };
                    $("." + q.attr("id") + "-click").click(expand_fn);
                    // return descendants for use by parent
                    return descendants;
                }
                // Initialize dict[parent_id] = rows_which_have_that_parent_id_as_parent_attr
                var par_child_dict = {},
                    no_parent = [];
                $(this).find("tbody tr").each( function() {
                    if ( $(this).attr("parent")) {
                        var parent = $(this).attr("parent");
                        if (par_child_dict[parent] !== undefined) {
                            par_child_dict[parent].push(this);
                        } else {
                            par_child_dict[parent] = [this];
                        }
                    } else {
                        no_parent.push(this);
                    }                        
                });
                $(no_parent).each( function() {
                    descendants = process_row( $(this), $([]) );
                    descendants.hide();
               });
            });
            restore_folder_state();
        };
        $(function() {
            init_dependencies();
        });
    </script>
</%def>

<%def name="render_sharable_str( repository )">
    <%
        from galaxy.util.shed_util_common import generate_citable_link_for_repository_in_tool_shed
        citable_str = generate_citable_link_for_repository_in_tool_shed( trans, repository )
    %>
    ${citable_str}
</%def>

<%def name="render_clone_str( repository )">
    <%
        from galaxy.util.shed_util_common import generate_clone_url_for_repository_in_tool_shed
        clone_str = generate_clone_url_for_repository_in_tool_shed( trans, repository )
    %>
    hg clone <a href="${clone_str}">${clone_str}</a>
</%def>

<%def name="render_folder( folder, folder_pad, parent=None, row_counter=None, is_root_folder=False )">
    <%
        encoded_id = trans.security.encode_id( folder.id )
        
        if is_root_folder:
            pad = folder_pad
            expander = h.url_for("/static/images/silk/resultset_bottom.png")
            folder_img = h.url_for("/static/images/silk/folder_page.png")
        else:
            pad = folder_pad + 20
            expander = h.url_for("/static/images/silk/resultset_next.png")
            folder_img = h.url_for("/static/images/silk/folder.png")
        my_row = None
    %>
    %if not is_root_folder:
        <%
            if parent is None:
                bg_str = 'bgcolor="#D8D8D8"'
            else:
                bg_str = ''
        %>
        <tr id="folder-${encoded_id}" ${bg_str} class="folderRow libraryOrFolderRow"
            %if parent is not None:
                parent="${parent}"
                style="display: none;"
            %endif
            >
            <%
                col_span_str = ''
                folder_label = str( folder.label )
                if folder.datatypes:
                    col_span_str = 'colspan="4"'
                elif folder.label == 'Missing tool dependencies':
                    if folder.description:
                        folder_label = "%s<i> - %s</i>" % ( folder_label, folder.description )
                    else:
                        folder_label = "%s<i> - repository tools require handling of these missing dependencies</i>" % folder_label
                    col_span_str = 'colspan="5"'
                elif folder.label in [ 'Installed repository dependencies', 'Repository dependencies', 'Missing repository dependencies' ]:
                    if folder.description:
                        folder_label = "%s<i> - %s</i>" % ( folder_label, folder.description )
                    elif folder.label not in [ 'Installed repository dependencies' ]:
                        folder_label = "%s<i> - installation of these additional repositories is required</i>" % folder_label
                    if trans.webapp.name == 'galaxy':
                        col_span_str = 'colspan="4"'
                elif folder.label == 'Valid tools':
                    col_span_str = 'colspan="3"'
                    if folder.description:
                        folder_label = "%s<i> - %s</i>" % ( folder_label, folder.description )
                    else:
                        folder_label = "%s<i> - click the name to preview the tool and use the pop-up menu to inspect all metadata</i>" % folder_label
                elif folder.invalid_tools:
                    folder_label = "%s<i> - click the tool config file name to see why the tool is invalid</i>" % folder_label
                elif folder.tool_dependencies:
                    if folder.description:
                        folder_label = "%s<i> - %s</i>" % ( folder_label, folder.description )
                    else:
                        folder_label = "%s<i> - repository tools require handling of these dependencies</i>" % folder_label
                    col_span_str = 'colspan="4"'
                elif folder.workflows:
                    if folder.description:
                        folder_label = "%s<i> - %s</i>" % ( folder_label, folder.description )
                    else:
                        folder_label = "%s<i> - click the name to view an SVG image of the workflow</i>" % folder_label
                    col_span_str = 'colspan="4"'
            %>
            <td ${col_span_str} style="padding-left: ${folder_pad}px;">
                <span class="expandLink folder-${encoded_id}-click">
                    <div style="float: left; margin-left: 2px;" class="expandLink folder-${encoded_id}-click">
                        <a class="folder-${encoded_id}-click" href="javascript:void(0);">
                            ${folder_label}
                        </a>
                    </div>
                </span>
            </td>
        </tr>
        <%
            my_row = row_counter.count
            row_counter.increment()  
        %>
    %endif
    %for sub_folder in folder.folders:
        ${render_folder( sub_folder, pad, parent=my_row, row_counter=row_counter, is_root_folder=False )}
    %endfor
    %for readme in folder.readme_files:
        ${render_readme( readme, pad, my_row, row_counter )}
    %endfor
    %for index, repository_dependency in enumerate( folder.repository_dependencies ):
        <% row_is_header = index == 0 %>
        ${render_repository_dependency( repository_dependency, pad, my_row, row_counter, row_is_header )}
    %endfor
    %for index, tool_dependency in enumerate( folder.tool_dependencies ):
        <% row_is_header = index == 0 %>
        ${render_tool_dependency( tool_dependency, pad, my_row, row_counter, row_is_header )}
    %endfor
    %if folder.valid_tools:
        %for index, tool in enumerate( folder.valid_tools ):
            <% row_is_header = index == 0 %>
            ${render_tool( tool, pad, my_row, row_counter, row_is_header )}
        %endfor
    %endif
    %for invalid_tool in folder.invalid_tools:
        ${render_invalid_tool( invalid_tool, pad, my_row, row_counter )}
    %endfor
    %if folder.workflows:
        %for index, workflow in enumerate( folder.workflows ):
            <% row_is_header = index == 0 %>
            ${render_workflow( workflow, pad, my_row, row_counter, row_is_header )}
        %endfor
    %endif
    %if folder.datatypes:
        %for index, datatype in enumerate( folder.datatypes ):
            <% row_is_header = index == 0 %>
            ${render_datatype( datatype, pad, my_row, row_counter, row_is_header )}
        %endfor
    %endif
</%def>

<%def name="render_datatype( datatype, pad, parent, row_counter, row_is_header=False )">
    <%
        encoded_id = trans.security.encode_id( datatype.id )
        if row_is_header:
            cell_type = 'th'
        else:
            cell_type = 'td'
    %>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-${encoded_id}">
        <${cell_type} style="padding-left: ${pad+20}px;">${datatype.extension | h}</${cell_type}>
        <${cell_type}>${datatype.type | h}</${cell_type}>
        <${cell_type}>${datatype.mimetype | h}</${cell_type}>
        <${cell_type}>${datatype.subclass | h}</${cell_type}>
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_invalid_tool( invalid_tool, pad, parent, row_counter, valid=True )">
    <% encoded_id = trans.security.encode_id( invalid_tool.id ) %>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-${encoded_id}">
        <td style="padding-left: ${pad+20}px;">
            %if trans.webapp.name == 'community' and invalid_tool.repository_id and invalid_tool.tool_config and invalid_tool.changeset_revision:
                <a class="view-info" href="${h.url_for( controller='repository', action='load_invalid_tool', repository_id=trans.security.encode_id( invalid_tool.repository_id ), tool_config=invalid_tool.tool_config, changeset_revision=invalid_tool.changeset_revision )}">
                    ${invalid_tool.tool_config | h}
                </a>
            %else:
                ${invalid_tool.tool_config | h}
            %endif
        </td>
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_readme( readme, pad, parent, row_counter )">
    <%
        from galaxy.util.shed_util_common import to_safe_string
        encoded_id = trans.security.encode_id( readme.id )
    %>
    <style type="text/css">
        #readme_table{ table-layout:fixed;
                       width:100%;
                       overflow-wrap:normal;
                       overflow:hidden;
                       border:0px; 
                       word-break:keep-all;
                       word-wrap:break-word;
                       line-break:strict; }
    </style>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-${encoded_id}">
        <td style="padding-left: ${pad+20}px;">
            <table id="readme_table">
                <tr><td>${ to_safe_string( readme.text, to_html=True ) }</td></tr>
            </table>
        </td>
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_repository_dependency( repository_dependency, pad, parent, row_counter, row_is_header=False )">
                
    <%
        encoded_id = trans.security.encode_id( repository_dependency.id )
        if trans.webapp.name == 'galaxy':
            if repository_dependency.tool_shed_repository_id:
                encoded_required_repository_id = trans.security.encode_id( repository_dependency.tool_shed_repository_id )
            else:
                encoded_required_repository_id = None
            if repository_dependency.installation_status:
                installation_status = str( repository_dependency.installation_status )
            else:
                installation_status = None
        repository_name = str( repository_dependency.repository_name )
        changeset_revision = str( repository_dependency.changeset_revision )
        repository_owner = str( repository_dependency.repository_owner )

        if trans.webapp.name == 'galaxy':
            if row_is_header:
                cell_type = 'th'
            else:
                cell_type = 'td'
        else:
            cell_type = 'td'
    %>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-${encoded_id}">
        %if trans.webapp.name == 'galaxy':
            <${cell_type} style="padding-left: ${pad+20}px;">
                %if row_is_header:
                    ${repository_name | h}
                %elif encoded_required_repository_id:
                    <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_repository', id=encoded_required_repository_id )}">${repository_name | h}</a>
                %else:
                   ${repository_name | h} 
                %endif
            </${cell_type}>
            <${cell_type}>
                ${changeset_revision | h}
            </${cell_type}>
            <${cell_type}>
                ${repository_owner | h}
            </${cell_type}>
            <${cell_type}>
                ${installation_status}
            </${cell_type}>
        %else:
            <td style="padding-left: ${pad+20}px;">
                Repository <b>${repository_name | h}</b> revision <b>${changeset_revision | h}</b> owned by <b>${repository_owner | h}</b>
            </td>
        %endif
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_tool( tool, pad, parent, row_counter, row_is_header )">
    <%
        encoded_id = trans.security.encode_id( tool.id )
        if row_is_header:
            cell_type = 'th'
        else:
            cell_type = 'td'
    %>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-${encoded_id}">
        %if row_is_header:
            <th style="padding-left: ${pad+20}px;">${tool.name | h}</th>
        %else:
            <td style="padding-left: ${pad+20}px;">
                %if tool.repository_id:
                    %if trans.webapp.name == 'community':
                        <div style="float:left;" class="menubutton split popup" id="tool-${encoded_id}-popup">
                            <a class="view-info" href="${h.url_for( controller='repository', action='display_tool', repository_id=trans.security.encode_id( tool.repository_id ), tool_config=tool.tool_config, changeset_revision=tool.changeset_revision )}">${tool.name | h}</a>
                        </div>
                        <div popupmenu="tool-${encoded_id}-popup">
                            <a class="action-button" href="${h.url_for( controller='repository', action='view_tool_metadata', repository_id=trans.security.encode_id( tool.repository_id ), changeset_revision=tool.changeset_revision, tool_id=tool.tool_id )}">View tool metadata</a>
                        </div>
                    %else:
                        %if tool.repository_installation_status == trans.model.ToolShedRepository.installation_status.INSTALLED:
                            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='view_tool_metadata', repository_id=trans.security.encode_id( tool.repository_id ), changeset_revision=tool.changeset_revision, tool_id=tool.tool_id )}">${tool.name | h}</a>
                        %else:
                            ${tool.name | h}
                        %endif
                    %endif
                %else:
                    ${tool.name | h}
                %endif
            </td>
        %endif
        <${cell_type}>${tool.description | h}</${cell_type}>
        <${cell_type}>${tool.version | h}</${cell_type}>
        ##<${cell_type}>${tool.requirements | h}</${cell_type}>
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_tool_dependency( tool_dependency, pad, parent, row_counter, row_is_header )">
    <%
        encoded_id = trans.security.encode_id( tool_dependency.id )
        is_missing = tool_dependency.installation_status not in [ 'Installed' ]
        if row_is_header:
            cell_type = 'th'
        else:
            cell_type = 'td'
    %>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-${encoded_id}">
        <${cell_type} style="padding-left: ${pad+20}px;">
            %if row_is_header:
                ${tool_dependency.name | h}
            %elif trans.webapp.name == 'galaxy' and tool_dependency.tool_dependency_id:
                %if tool_dependency.repository_id and tool_dependency.installation_status == 'Installed':
                    <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_tool_dependency', id=trans.security.encode_id( tool_dependency.tool_dependency_id ), repository_id=trans.security.encode_id( tool_dependency.repository_id ) )}">
                        ${tool_dependency.name | h}
                    </a>
                %elif tool_dependency.installation_status != 'Installed':
                    <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_tool_dependencies', id=trans.security.encode_id( tool_dependency.tool_dependency_id ) )}">
                        ${tool_dependency.name}
                    </a>
                %else:
                    ${tool_dependency.name | h}
                %endif
            %else:
                ${tool_dependency.name | h}
            %endif
        </${cell_type}>
        <${cell_type}>
            <%
                if tool_dependency.version:
                    version_str = tool_dependency.version
                else:
                    version_str = ''
            %>
            ${version_str | h}
        </${cell_type}>
        <${cell_type}>${tool_dependency.type | h}</${cell_type}>
        %if trans.webapp.name == 'galaxy':
            %if is_missing:
                <${cell_type}>${tool_dependency.installation_status | h}</${cell_type}>
            %elif tool_dependency.install_dir:
                <${cell_type}>${tool_dependency.install_dir | h}</${cell_type}>
            %endif
        %endif
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_workflow( workflow, pad, parent, row_counter, row_is_header=False )">
    <%
        from galaxy.tool_shed.encoding_util import tool_shed_encode
        encoded_id = trans.security.encode_id( workflow.id )
        encoded_workflow_name = tool_shed_encode( workflow.workflow_name )
        if trans.webapp.name == 'community':
            encoded_repository_metadata_id = trans.security.encode_id( workflow.repository_metadata_id )
            encoded_repository_id = None
        else:
            encoded_repository_metadata_id = None
            encoded_repository_id = trans.security.encode_id( workflow.repository_id )
        if row_is_header:
            cell_type = 'th'
        else:
            cell_type = 'td'
    %>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-${encoded_id}">
        <${cell_type} style="padding-left: ${pad+20}px;">
            %if row_is_header:
                ${workflow.workflow_name | h}
            %elif trans.webapp.name == 'community' and encoded_repository_metadata_id:
                <a href="${h.url_for( controller='repository', action='view_workflow', workflow_name=encoded_workflow_name, repository_metadata_id=encoded_repository_metadata_id )}">${workflow.workflow_name | h}</a>
            %elif trans.webapp.name == 'galaxy' and encoded_repository_id:
                <a href="${h.url_for( controller='admin_toolshed', action='view_workflow', workflow_name=encoded_workflow_name, repository_id=encoded_repository_id )}">${workflow.workflow_name | h}</a>
            %else:
                ${workflow.workflow_name | h}
            %endif
        </${cell_type}>
        <${cell_type}>${workflow.steps | h}</${cell_type}>
        <${cell_type}>${workflow.format_version | h}</${cell_type}>
        <${cell_type}>${workflow.annotation | h}</${cell_type}>
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_repository_items( metadata, containers_dict, can_set_metadata=False )">
    <%
        from galaxy.tool_shed.encoding_util import tool_shed_encode

        has_datatypes = metadata and 'datatypes' in metadata
        has_readme_files = metadata and 'readme_files' in metadata
        has_workflows = metadata and 'workflows' in metadata
        
        datatypes_root_folder = containers_dict.get( 'datatypes', None )
        invalid_tools_root_folder = containers_dict.get( 'invalid_tools', None )
        readme_files_root_folder = containers_dict.get( 'readme_files', None )
        repository_dependencies_root_folder = containers_dict.get( 'repository_dependencies', None )
        missing_repository_dependencies_root_folder = containers_dict.get( 'missing_repository_dependencies', None )
        tool_dependencies_root_folder = containers_dict.get( 'tool_dependencies', None )
        missing_tool_dependencies_root_folder = containers_dict.get( 'missing_tool_dependencies', None )
        valid_tools_root_folder = containers_dict.get( 'valid_tools', None )
        workflows_root_folder = containers_dict.get( 'workflows', None )
        
        has_contents = datatypes_root_folder or invalid_tools_root_folder or valid_tools_root_folder or workflows_root_folder

        class RowCounter( object ):
            def __init__( self ):
                self.count = 0
            def increment( self ):
                self.count += 1
            def __str__( self ):
                return str( self.count )
    %>
    %if readme_files_root_folder:
        <div class="toolForm">
            <div class="toolFormTitle">Repository README files - may contain important installation or license information</div>
            <div class="toolFormBody">
                <p/>
                <% row_counter = RowCounter() %>
                <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="readme_files">
                    ${render_folder( readme_files_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
                </table>
            </div>
        </div>
    %endif
    %if missing_repository_dependencies_root_folder or repository_dependencies_root_folder or tool_dependencies_root_folder or missing_tool_dependencies_root_folder:
        <div class="toolForm">
            <div class="toolFormTitle">Dependencies of this repository</div>
            <div class="toolFormBody">
                %if missing_repository_dependencies_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="missing_repository_dependencies">
                        ${render_folder( missing_repository_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
                    </table>
                %endif
                %if repository_dependencies_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="repository_dependencies">
                        ${render_folder( repository_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
                    </table>
                %endif
                %if tool_dependencies_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="tool_dependencies">
                        ${render_folder( tool_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
                    </table>
                %endif
                %if missing_tool_dependencies_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="missing_tool_dependencies">
                        ${render_folder( missing_tool_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
                    </table>
                %endif
            </div>
        </div>
    %endif
    %if has_contents:
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">Contents of this repository</div>
            <div class="toolFormBody">
                %if valid_tools_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="valid_tools">
                        ${render_folder( valid_tools_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
                    </table>
                %endif
                %if invalid_tools_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="invalid_tools">
                        ${render_folder( invalid_tools_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
                    </table>
                %endif
                %if workflows_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="workflows">
                        ${render_folder( workflows_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
                    </table>
                %endif
                %if datatypes_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="datatypes">
                        ${render_folder( datatypes_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True )}
                    </table>
                %endif
            </div>
        </div>
    %endif
</%def>
