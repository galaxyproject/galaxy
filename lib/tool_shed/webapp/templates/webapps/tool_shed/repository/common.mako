<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%def name="common_javascripts(repository)">
    <script type="text/javascript">
        config.addInitialization(function() {
            console.log("common.mako, common_javascripts");

            // --- Initialize sample trees
            $("#tree").dynatree({
                title: "${repository.name}",
                minExpandLevel: 1,
                persist: false,
                checkbox: true,
                selectMode: 3,
                onPostInit: function(isReloading, isError) {
                    // Re-fire onActivate, so the text is updated
                    this.reactivate();
                },
                fx: { height: "toggle", duration: 200 },
                // initAjax is hard to fake, so we pass the children as object array:
                initAjax: {url: "${h.url_for( controller='repository', action='open_folder' )}",
                           dataType: "json",
                           data: { folder_path: "${repository.repo_path( trans.app )}", repository_id: "${trans.security.encode_id( repository.id )}"  },
                },
                onLazyRead: function(dtnode){
                    dtnode.appendAjax({
                        url: "${h.url_for( controller='repository', action='open_folder' )}",
                        dataType: "json",
                        data: { folder_path: dtnode.data.key, repository_id: "${trans.security.encode_id( repository.id )}"  },
                    });
                },
                onSelect: function(select, dtnode) {
                    // Display list of selected nodes
                    var selNodes = dtnode.tree.getSelectedNodes();
                    // convert to title/key array
                    var selKeys = $.map(selNodes, function(node) {
                        return node.data.key;
                    });
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
                            data: { file_path: selected_value, repository_id: "${trans.security.encode_id( repository.id )}" },
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
        config.addInitialization(function() {
            console.log("common.mako, container_javascripts");

            var store = window.bundleToolshed.store;
            var init_dependencies = function() {
                var storage_id = "library-expand-state-${trans.security.encode_id(10000)}";
                var restore_folder_state = function() {
                    var state = store.get(storage_id);
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
                    store.set(storage_id, state);
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

            var init_clipboard = function() {
                %if hasattr( repository, 'clone_url' ):
                    $('#clone_clipboard').on('click', function( event ) {
                        event.preventDefault();
                        window.prompt("Copy to clipboard: Ctrl+C, Enter", "hg clone ${ repository.clone_url }");
                    });
                %endif
                %if hasattr( repository, 'share_url' ):
                    $('#share_clipboard').on('click', function( event ) {
                        event.preventDefault();
                        window.prompt("Copy to clipboard: Ctrl+C, Enter", "${ repository.share_url }");
                    });
                %endif
            };

            init_dependencies();
            init_clipboard();
        });
    </script>
</%def>

<%def name="render_repository_type_select_field( repository_type_select_field, render_help=True )">
    <div class="form-row">
        <label>Repository type:</label>
        <%
            from tool_shed.repository_types import util
            options = repository_type_select_field.options
            repository_types = []
            for option_tup in options:
                repository_types.append( option_tup[ 1 ] )
            render_as_text = len( options ) == 1
            if render_as_text:
                repository_type = options[ 0 ][ 0 ]
        %>
        %if render_as_text:
            ${repository_type | h}
            %if render_help:
                <div class="toolParamHelp" style="clear: both;">
                    This repository's type cannot be changed because its contents are valid only for its current type or it has been cloned.
                </div>
            %endif
        %else:
            ${render_select(repository_type_select_field)}
            %if render_help:
                <div class="toolParamHelp" style="clear: both;">
                    Select the repository type based on the following criteria.
                    <ul>
                        %if util.UNRESTRICTED in repository_types:
                            <li><b>Unrestricted</b> - contents can be any set of valid Galaxy utilities or files
                        %endif
                        %if util.REPOSITORY_SUITE_DEFINITION in repository_types:
                            <li><b>Repository suite definition</b> - contents will always be restricted to one file named repository_dependencies.xml
                        %endif
                        %if util.TOOL_DEPENDENCY_DEFINITION in repository_types:
                            <li><b>Tool dependency definition</b> - contents will always be restricted to one file named tool_dependencies.xml
                        %endif
                    </ul>
                </div>
            %endif
        %endif
        <div style="clear: both"></div>
    </div>
</%def>

<%def name="render_sharable_str( repository, changeset_revision=None )">
    <%
        from tool_shed.util.repository_util import generate_sharable_link_for_repository_in_tool_shed
        sharable_link = generate_sharable_link_for_repository_in_tool_shed( repository, changeset_revision=changeset_revision )
    %>
    <a href="${ sharable_link }" target="_blank">${ sharable_link }</a>
</%def>

<%def name="render_clone_str( repository )"><%
        from tool_shed.util.common_util import generate_clone_url_for_repository_in_tool_shed
        clone_str = generate_clone_url_for_repository_in_tool_shed( trans.user, repository )
    %>hg clone ${ clone_str }</%def>

<%def name="render_folder( folder, folder_pad, parent=None, row_counter=None, is_root_folder=False, render_repository_actions_for='tool_shed' )">
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
                    elif folder.label not in [ 'Installed repository dependencies' ] and folder.parent.label not in [ 'Installation errors' ]:
                        folder_label = "%s<i> - installation of these additional repositories is required</i>" % folder_label
                    if trans.webapp.name == 'galaxy':
                        col_span_str = 'colspan="4"'
                elif folder.label == 'Invalid repository dependencies':
                    folder_label = "%s<i> - click the repository dependency to see why it is invalid</i>" % folder_label
                elif folder.label == 'Invalid tool dependencies':
                    folder_label = "%s<i> - click the tool dependency to see why it is invalid</i>" % folder_label
                elif folder.label == 'Valid tools':
                    col_span_str = 'colspan="4"'
                    if folder.description:
                        folder_label = "%s<i> - %s</i>" % ( folder_label, folder.description )
                    else:
                        folder_label = "%s<i> - click the name to preview the tool and use the pop-up menu to inspect all metadata</i>" % folder_label
                elif folder.invalid_tools:
                    if trans.webapp.name == 'tool_shed':
                        folder_label = "%s<i> - click the tool config file name to see why the tool is invalid</i>" % folder_label
                elif folder.tool_dependencies:
                    if folder.description:
                        folder_label = "%s<i> - %s</i>" % ( folder_label, folder.description )
                    else:
                        folder_label = "%s<i> - repository tools require handling of these dependencies</i>" % folder_label
                    col_span_str = 'colspan="4"'
                elif folder.valid_data_managers:
                    if folder.description:
                        folder_label = "%s<i> - %s</i>" % ( folder_label, folder.description )
                    col_span_str = 'colspan="3"'
                elif folder.invalid_data_managers:
                    if folder.description:
                        folder_label = "%s<i> - %s</i>" % ( folder_label, folder.description )
                    col_span_str = 'colspan="2"'
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
        ${render_folder( sub_folder, pad, parent=my_row, row_counter=row_counter, is_root_folder=False, render_repository_actions_for=render_repository_actions_for )}
    %endfor
    %for readme in folder.readme_files:
        ${render_readme( readme, pad, my_row, row_counter, render_repository_actions_for=render_repository_actions_for )}
    %endfor
    %for invalid_repository_dependency in folder.invalid_repository_dependencies:
        ${render_invalid_repository_dependency( invalid_repository_dependency, pad, my_row, row_counter, render_repository_actions_for=render_repository_actions_for )}
    %endfor
    %for index, repository_dependency in enumerate( folder.repository_dependencies ):
        <% row_is_header = index == 0 %>
        ${render_repository_dependency( repository_dependency, pad, my_row, row_counter, row_is_header, render_repository_actions_for=render_repository_actions_for )}
    %endfor
    %for invalid_tool_dependency in folder.invalid_tool_dependencies:
        ${render_invalid_tool_dependency( invalid_tool_dependency, pad, my_row, row_counter, render_repository_actions_for=render_repository_actions_for )}
    %endfor
    %for index, tool_dependency in enumerate( folder.tool_dependencies ):
        <% row_is_header = index == 0 %>
        ${render_tool_dependency( tool_dependency, pad, my_row, row_counter, row_is_header, render_repository_actions_for=render_repository_actions_for )}
    %endfor
    %if folder.valid_tools:
        %for index, tool in enumerate( folder.valid_tools ):
            <% row_is_header = index == 0 %>
            ${render_tool( tool, pad, my_row, row_counter, row_is_header, render_repository_actions_for=render_repository_actions_for )}
        %endfor
    %endif
    %for invalid_tool in folder.invalid_tools:
        ${render_invalid_tool( invalid_tool, pad, my_row, row_counter, render_repository_actions_for=render_repository_actions_for )}
    %endfor
    %if folder.datatypes:
        %for index, datatype in enumerate( folder.datatypes ):
            <% row_is_header = index == 0 %>
            ${render_datatype( datatype, pad, my_row, row_counter, row_is_header, render_repository_actions_for=render_repository_actions_for )}
        %endfor
    %endif
    %if folder.valid_data_managers:
        %for index, data_manager in enumerate( folder.valid_data_managers ):
            <% row_is_header = index == 0 %>
            ${render_valid_data_manager( data_manager, pad, my_row, row_counter, row_is_header, render_repository_actions_for=render_repository_actions_for )}
        %endfor
    %endif
    %if folder.invalid_data_managers:
        %for index, data_manager in enumerate( folder.invalid_data_managers ):
            <% row_is_header = index == 0 %>
            ${render_invalid_data_manager( data_manager, pad, my_row, row_counter, row_is_header, render_repository_actions_for=render_repository_actions_for )}
        %endfor
    %endif
    %if folder.missing_test_components:
        %for missing_test_component in folder.missing_test_components:
            ${render_missing_test_component( missing_test_component, pad, my_row, row_counter, render_repository_actions_for=render_repository_actions_for )}
        %endfor
    %endif
</%def>

<%def name="render_datatype( datatype, pad, parent, row_counter, row_is_header=False, render_repository_actions_for='tool_shed' )">
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
        id="libraryItem-rd-${encoded_id}">
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

<%def name="render_invalid_data_manager( data_manager, pad, parent, row_counter, row_is_header=False, render_repository_actions_for='tool_shed' )">
    <%
        encoded_id = trans.security.encode_id( data_manager.id )
        if row_is_header:
            cell_type = 'th'
        else:
            cell_type = 'td'
    %>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-ridm-${encoded_id}">
        <${cell_type} style="padding-left: ${pad+20}px;">${data_manager.index | h}</${cell_type}>
        <${cell_type}>${data_manager.error | h}</${cell_type}>
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_invalid_repository_dependency( invalid_repository_dependency, pad, parent, row_counter, render_repository_actions_for='tool_shed' )">
    <%
        encoded_id = trans.security.encode_id( invalid_repository_dependency.id )
    %>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-rird-${encoded_id}">
        <td style="padding-left: ${pad+20}px;">
            ${ invalid_repository_dependency.error | h }
        </td>
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_invalid_tool( invalid_tool, pad, parent, row_counter, valid=True, render_repository_actions_for='tool_shed' )">
    <% encoded_id = trans.security.encode_id( invalid_tool.id ) %>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-rit-${encoded_id}">
        <td style="padding-left: ${pad+20}px;">
            %if trans.webapp.name == 'tool_shed' and invalid_tool.repository_id and invalid_tool.tool_config and invalid_tool.changeset_revision:
                <a class="view-info" href="${h.url_for( controller='repository', action='load_invalid_tool', repository_id=trans.security.encode_id( invalid_tool.repository_id ), tool_config=invalid_tool.tool_config, changeset_revision=invalid_tool.changeset_revision, render_repository_actions_for=render_repository_actions_for )}">
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

<%def name="render_invalid_tool_dependency( invalid_tool_dependency, pad, parent, row_counter, render_repository_actions_for='tool_shed' )">
    <%
        encoded_id = trans.security.encode_id( invalid_tool_dependency.id )
    %>
    <style type="text/css">
        #invalid_td_table{ table-layout:fixed;
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
        id="libraryItem-ritd-${encoded_id}">
        <td style="padding-left: ${pad+20}px;">
            <table id="invalid_td_table">
                <tr><td>${ invalid_tool_dependency.error | h }</td></tr>
            </table>
        </td>
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_missing_test_component( missing_test_component, pad, parent, row_counter, row_is_header=False, render_repository_actions_for='tool_shed' )">
    <%
        encoded_id = trans.security.encode_id( missing_test_component.id )
    %>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-rmtc-${encoded_id}">
        <td style="padding-left: ${pad+20}px;">
            <table id="test_environment">
                <tr><td bgcolor="#FFFFCC"><b>Tool id:</b> ${missing_test_component.tool_id | h}</td></tr>
                <tr><td><b>Tool version:</b> ${missing_test_component.tool_version | h}</td></tr>
                <tr><td><b>Tool guid:</b> ${missing_test_component.tool_guid | h}</td></tr>
                <tr><td><b>Missing components:</b> <br/>${missing_test_component.missing_components | h}</td></tr>
            </table>
        </td>
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_readme( readme, pad, parent, row_counter, render_repository_actions_for='tool_shed' )">
    <% encoded_id = trans.security.encode_id( readme.id ) %>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-rr-${encoded_id}">
        <td style="padding-left: ${pad+20}px;">
            <table id="readme_files">
                <tr><td>${ readme.text }</td></tr>
            </table>
        </td>
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_repository_dependency( repository_dependency, pad, parent, row_counter, row_is_header=False, render_repository_actions_for='tool_shed' )">
    <%
        from galaxy.util import asbool
        from tool_shed.util.repository_util import get_repository_by_name_and_owner
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
        repository_owner = str( repository_dependency.repository_owner )
        changeset_revision = str( repository_dependency.changeset_revision )
        if asbool( str( repository_dependency.prior_installation_required ) ):
            prior_installation_required_str = " <i>(prior install required)</i>"
        else:
            prior_installation_required_str = ""
        if trans.webapp.name == 'galaxy':
            if row_is_header:
                cell_type = 'th'
            else:
                cell_type = 'td'
            rd = None
        else:
            # We're in the tool shed.
            cell_type = 'td'
            rd = get_repository_by_name_and_owner( trans.app, repository_name, repository_owner )
    %>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-rrd-${encoded_id}">
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
                %if render_repository_actions_for == 'tool_shed' and rd:
                    <a class="view-info" href="${h.url_for( controller='repository', action='view_or_manage_repository', id=trans.security.encode_id( rd.id ), changeset_revision=changeset_revision )}">Repository <b>${repository_name | h}</b> revision <b>${changeset_revision | h}</b> owned by <b>${repository_owner | h}</b></a>${prior_installation_required_str}
                %else:
                    Repository <b>${repository_name | h}</b> revision <b>${changeset_revision | h}</b> owned by <b>${repository_owner | h}</b>${prior_installation_required_str}
                %endif
            </td>
        %endif
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_table_wrap_style( table_id )">
    <style type="text/css">
        table.${table_id}{ table-layout:fixed;
                           width:100%;
                           overflow-wrap:normal;
                           overflow:hidden;
                           border:0px;
                           word-break:keep-all;
                           word-wrap:break-word;
                           line-break:strict; }
        ul{ list-style-type: disc;
            padding-left: 20px; }
    </style>
</%def>

<%def name="render_tool( tool, pad, parent, row_counter, row_is_header, render_repository_actions_for='tool_shed' )">
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
        id="libraryItem-rt-${encoded_id}">
        %if row_is_header:
            <th style="padding-left: ${pad+20}px;">${tool.name | h}</th>
        %else:
            <td style="padding-left: ${pad+20}px;">
                %if tool.repository_id:
                    %if trans.webapp.name == 'tool_shed':
                        <div style="float:left;" class="menubutton split popup" id="tool-${encoded_id}-popup">
                            <a class="view-info" href="${h.url_for( controller='repository', action='display_tool', repository_id=trans.security.encode_id( tool.repository_id ), tool_config=tool.tool_config, changeset_revision=tool.changeset_revision, render_repository_actions_for=render_repository_actions_for )}">${tool.name | h}</a>
                        </div>
                        <div popupmenu="tool-${encoded_id}-popup">
                            <a class="action-button" href="${h.url_for( controller='repository', action='view_tool_metadata', repository_id=trans.security.encode_id( tool.repository_id ), changeset_revision=tool.changeset_revision, tool_id=tool.tool_id, render_repository_actions_for=render_repository_actions_for )}">View tool metadata</a>
                        </div>
                    %elif trans.webapp.name == 'galaxy':
                        %if tool.repository_installation_status == trans.install_model.ToolShedRepository.installation_status.INSTALLED:
                            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='view_tool_metadata', repository_id=trans.security.encode_id( tool.repository_id ), changeset_revision=tool.changeset_revision, tool_id=tool.tool_id )}">${tool.name | h}</a>
                        %else:
                            ${tool.name | h}
                        %endif
                    %else:
                        ${tool.name | h}
                    %endif
                %else:
                    ${tool.name | h}
                %endif
            </td>
        %endif
        <${cell_type}>${tool.description | h}</${cell_type}>
        <${cell_type}>${tool.version | h}</${cell_type}>
        <${cell_type}>${tool.profile | h}</${cell_type}>
        ##<${cell_type}>${tool.requirements | h}</${cell_type}>
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_tool_dependency( tool_dependency, pad, parent, row_counter, row_is_header, render_repository_actions_for='tool_shed' )">
    <%
        from galaxy.util import string_as_bool
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
        id="libraryItem-rtd-${encoded_id}">
        <${cell_type} style="padding-left: ${pad+20}px;">
            %if row_is_header:
                ${tool_dependency.name | h}
            %elif trans.webapp.name == 'galaxy' and tool_dependency.tool_dependency_id:
                %if tool_dependency.repository_id and tool_dependency.installation_status in [ trans.install_model.ToolDependency.installation_status.INSTALLED ]:
                    <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_tool_dependency', id=trans.security.encode_id( tool_dependency.tool_dependency_id ) )}">
                        ${tool_dependency.name | h}
                    </a>
                %elif tool_dependency.installation_status not in [ trans.install_model.ToolDependency.installation_status.UNINSTALLED ]:
                    <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_repository_tool_dependencies', tool_dependency_ids=trans.security.encode_id( tool_dependency.tool_dependency_id ) )}">
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
        <${cell_type}>
            %if trans.webapp.name == 'galaxy':
                ${tool_dependency.installation_status | h}
            %endif
        </${cell_type}>
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_valid_data_manager( data_manager, pad, parent, row_counter, row_is_header=False, render_repository_actions_for='tool_shed' )">
    <%
        encoded_id = trans.security.encode_id( data_manager.id )
        if row_is_header:
            cell_type = 'th'
        else:
            cell_type = 'td'
    %>
    <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
        %endif
        id="libraryItem-rvdm-${encoded_id}">
        <${cell_type} style="padding-left: ${pad+20}px;">${data_manager.name | h}</${cell_type}>
        <${cell_type}>${data_manager.version | h}</${cell_type}>
        <${cell_type}>${data_manager.data_tables | h}</${cell_type}>
    </tr>
    <%
        my_row = row_counter.count
        row_counter.increment()
    %>
</%def>

<%def name="render_dependency_status( dependency, prepare_for_install=False)">
    <td>${dependency['name'] | h}</td>
    <td>${dependency['version'] | h}</td>
    %if not prepare_for_install:
        %if dependency['dependency_type']:
            <td>${dependency['dependency_type'].title() | h}</td>
        %else:
            <td>${dependency['dependency_type'] | h}</td>
        %endif
        <td>${dependency['exact'] | h}</td>
    %endif
    %if dependency['dependency_type'] == None:
        <td>
           <img src="${h.url_for('/static')}/images/icon_error_sml.gif" title='Dependency not resolved'/>
           %if prepare_for_install:
               Not Installed
           %endif
        </td>
    %elif not dependency['exact']:
        <td>
            <img src="${h.url_for('/static')}/images/icon_warning_sml.gif" title='Dependency resolved, but version ${dependency['version']} not found'/>
        </td>
    %else:
        <td>
            <img src="${h.url_for('/static')}/style/ok_small.png"/>
            %if prepare_for_install:
                Installed through ${dependency['dependency_type'].title() | h}
            %endif
        </td>
    %endif
</%def>

<%def name="render_tool_dependency_resolver( requirements_status, prepare_for_install=False )">
    <tr class="datasetRow">
        <td style="padding-left: 20 px;">
            <table class="grid" id="module_resolver_environment">
                <head>
                    <tr>
                        <th>Dependency</th>
                        <th>Version</th>
                        %if not prepare_for_install:
                            <th>Resolver</th>
                            <th>Exact version</th>
                        %endif
                        <th>Current Installation Status<th>
                    </tr>
                </head>
                <body>
                    %for dependency in requirements_status:
                        ${render_dependency_status(dependency, prepare_for_install)}
                        <tr>
                    %endfor
                </body>
            </table>
        </td>
    </tr>
</%def>

<%def name="render_resolver_dependencies( requirements_status )">
    %if requirements_status:
        <div class="card">
            <div class="card-header">Dependency Resolver Details</div>
            <div class="card-body">
                <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="module_resolvers">
                    ${render_tool_dependency_resolver( requirements_status )}
                </table>
            </div>
        </div>
    %endif
</%def>

<%def name="render_repository_items( metadata, containers_dict, can_set_metadata=False, render_repository_actions_for='tool_shed' )">
    <%
        from galaxy.util.tool_shed.encoding_util import tool_shed_encode

        has_datatypes = metadata and 'datatypes' in metadata
        has_readme_files = metadata and 'readme_files' in metadata

        datatypes_root_folder = containers_dict.get( 'datatypes', None )
        invalid_data_managers_root_folder = containers_dict.get( 'invalid_data_managers', None )
        invalid_repository_dependencies_root_folder = containers_dict.get( 'invalid_repository_dependencies', None )
        invalid_tool_dependencies_root_folder = containers_dict.get( 'invalid_tool_dependencies', None )
        invalid_tools_root_folder = containers_dict.get( 'invalid_tools', None )
        missing_repository_dependencies_root_folder = containers_dict.get( 'missing_repository_dependencies', None )
        missing_tool_dependencies_root_folder = containers_dict.get( 'missing_tool_dependencies', None )
        readme_files_root_folder = containers_dict.get( 'readme_files', None )
        repository_dependencies_root_folder = containers_dict.get( 'repository_dependencies', None )
        test_environment_root_folder = containers_dict.get( 'test_environment', None )
        tool_dependencies_root_folder = containers_dict.get( 'tool_dependencies', None )
        tool_test_results_root_folder = containers_dict.get( 'tool_test_results', None )
        valid_data_managers_root_folder = containers_dict.get( 'valid_data_managers', None )
        valid_tools_root_folder = containers_dict.get( 'valid_tools', None )

        has_contents = datatypes_root_folder or invalid_tools_root_folder or valid_tools_root_folder
        has_dependencies = \
            invalid_repository_dependencies_root_folder or \
            invalid_tool_dependencies_root_folder or \
            missing_repository_dependencies_root_folder or \
            repository_dependencies_root_folder or \
            tool_dependencies_root_folder or \
            missing_tool_dependencies_root_folder

        class RowCounter( object ):
            def __init__( self ):
                self.count = 0
            def increment( self ):
                self.count += 1
            def __str__( self ):
                return str( self.count )
    %>
    %if readme_files_root_folder:
        ${render_table_wrap_style( "readme_files" )}
        <p/>
        <div class="card">
            <div class="card-header">Repository README files - may contain important installation or license information</div>
            <div class="card-body">
                <p/>
                <% row_counter = RowCounter() %>
                <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="readme_files">
                    ${render_folder( readme_files_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True, render_repository_actions_for=render_repository_actions_for )}
                </table>
            </div>
        </div>
    %endif
    %if has_dependencies:
        <div class="card">
            <div class="card-header">Dependencies of this repository</div>
            <div class="card-body">
                %if invalid_repository_dependencies_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="invalid_repository_dependencies">
                        ${render_folder( invalid_repository_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True, render_repository_actions_for=render_repository_actions_for )}
                    </table>
                %endif
                %if missing_repository_dependencies_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="missing_repository_dependencies">
                        ${render_folder( missing_repository_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True, render_repository_actions_for=render_repository_actions_for )}
                    </table>
                %endif
                %if repository_dependencies_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="repository_dependencies">
                        ${render_folder( repository_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True, render_repository_actions_for=render_repository_actions_for )}
                    </table>
                %endif
                %if invalid_tool_dependencies_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="invalid_tool_dependencies">
                        ${render_folder( invalid_tool_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True, render_repository_actions_for=render_repository_actions_for )}
                    </table>
                %endif
                %if tool_dependencies_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="tool_dependencies">
                        ${render_folder( tool_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True, render_repository_actions_for=render_repository_actions_for )}
                    </table>
                %endif
                %if missing_tool_dependencies_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="missing_tool_dependencies">
                        ${render_folder( missing_tool_dependencies_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True, render_repository_actions_for=render_repository_actions_for )}
                    </table>
                %endif
            </div>
        </div>
    %endif
    %if has_contents:
        <p/>
        <div class="card">
            <div class="card-header">Contents of this repository</div>
            <div class="card-body">
                %if valid_tools_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="valid_tools">
                        ${render_folder( valid_tools_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True, render_repository_actions_for=render_repository_actions_for )}
                    </table>
                %endif
                %if invalid_tools_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="invalid_tools">
                        ${render_folder( invalid_tools_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True, render_repository_actions_for=render_repository_actions_for )}
                    </table>
                %endif
                %if valid_data_managers_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="valid_data_managers">
                        ${render_folder( valid_data_managers_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True, render_repository_actions_for=render_repository_actions_for )}
                    </table>
                %endif
                %if invalid_data_managers_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="invalid_data_managers">
                        ${render_folder( invalid_data_managers_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True, render_repository_actions_for=render_repository_actions_for )}
                    </table>
                %endif
                %if datatypes_root_folder:
                    <p/>
                    <% row_counter = RowCounter() %>
                    <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="datatypes">
                        ${render_folder( datatypes_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True, render_repository_actions_for=render_repository_actions_for )}
                    </table>
                %endif
            </div>
        </div>
    %endif
    %if tool_test_results_root_folder and trans.app.config.display_legacy_test_results:
        ${render_table_wrap_style( "test_environment" )}
        <p/>
        <div class="card">
            <div class="card-header">Automated tool test results</div>
            <div class="card-body">
                <p/>
                <% row_counter = RowCounter() %>
                <table cellspacing="2" cellpadding="2" border="0" width="100%" class="tables container-table" id="test_environment">
                    ${render_folder( tool_test_results_root_folder, 0, parent=None, row_counter=row_counter, is_root_folder=True, render_repository_actions_for=render_repository_actions_for )}
                </table>
            </div>
        </div>
    %endif
</%def>
