<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%
    from galaxy.util.expressions import ExpressionContext
    from galaxy import util
    from galaxy.tools.parameters.basic import DataToolParameter, ColumnListParameter, GenomeBuildParameter, SelectToolParameter
    from galaxy.web.form_builder import SelectField

    is_admin = trans.user_is_admin()
    is_new = repository.is_new
    can_contact_owner = trans.user and trans.user != repository.user
    can_push = trans.app.security_agent.can_push( trans.user, repository )
    can_upload = can_push
    can_download = not is_new and ( not is_malicious or can_push )
    can_browse_contents = not is_new
    can_rate = trans.user and repository.user != trans.user
    can_manage = is_admin or repository.user == trans.user
    can_view_change_log = not is_new
    if can_push:
        browse_label = 'Browse or delete repository tip files'
    else:
        browse_label = 'Browse repository tip files'
%>

<html>
    <head>
        <title>Galaxy tool preview</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        ${h.css( "base" )}
    </head>
    <body>
        <%def name="do_inputs( inputs, tool_state, prefix, other_values=None )">
            <% other_values = ExpressionContext( tool_state, other_values ) %>
            %for input_index, input in enumerate( inputs.itervalues() ):
                %if not input.visible:
                    <% pass %>
                %elif input.type == "repeat":
                    <div class="repeat-group">
                        <div class="form-title-row">
                            <b>${input.title_plural}</b>
                        </div>
                        <div class="repeat-group-item">
                            <div class="form-title-row">
                                <b>${input.title} 0</b>
                            </div>
                        </div>
                    </div>
                %elif input.type == "conditional":
                    %if tool_state.items():
                        <%
                            group_state = tool_state[input.name][0]
                            current_case = group_state['__current_case__']
                            group_prefix = prefix + input.name + "|"
                        %>
                        %if input.value_ref_in_group:
                            ${row_for_param( group_prefix, input.test_param, group_state, other_values )}
                        %endif
                        ${do_inputs( input.cases[current_case].inputs, group_state, group_prefix, other_values )}
                    %endif
                %elif input.type == "upload_dataset":
                    %if input.get_datatype( trans, other_values ).composite_type is None:
                        ## Have non-composite upload appear as before
                        ${do_inputs( input.inputs, 'files', prefix + input.name + "_" + str( 0 ) + "|", other_values )}
                    %else:
                        <div class="repeat-group">
                            <div class="form-title-row">
                                <b>${input.group_title( other_values )}</b>
                            </div>
                            <div class="repeat-group-item">
                            <div class="form-title-row">
                                <b>File Contents for ${input.title_by_index( trans, 0, other_values )}</b>
                            </div>
                        </div>
                    %endif
                %else:
                    ${row_for_param( prefix, input, tool_state, other_values )}
                %endif
            %endfor  
        </%def>
        
        <%def name="row_for_param( prefix, param, parent_state, other_values )">
            <%
                label = param.get_label()
                if isinstance( param, DataToolParameter ) or isinstance( param, ColumnListParameter ) or isinstance( param, GenomeBuildParameter ):
                    field = SelectField( param.name )
                    field.add_option( param.name, param.name )
                    field_html = field.get_html()
                elif isinstance( param, SelectToolParameter ) and hasattr( param, 'data_ref' ):
                    field = SelectField( param.name, display=param.display )
                    field.add_option( param.data_ref, param.data_ref )
                    field_html = field.get_html( prefix )
                elif isinstance( param, SelectToolParameter ) and param.is_dynamic:
                    field = SelectField( param.name, display=param.display )
                    dynamic_options = param.options
                    if dynamic_options.index_file:
                        option_label = "Dynamically generated from entries in file %s" % str( dynamic_options.index_file )
                        field.add_option( option_label, "none" )
                    elif dynamic_options.missing_index_file:
                        option_label = "Dynamically generated from entries in missing file %s" % str( dynamic_options.missing_index_file )
                        field.add_option( option_label, "none" )
                    field_html = field.get_html( prefix )
                else:
                    field = param.get_html_field( trans, None, other_values )
                    field_html = field.get_html( prefix )
            %>
            <div class="form-row">
                %if label:
                    <label for="${param.name}">${label}:</label>
                %endif
                <div class="form-row-input">${field_html}</div>
                %if param.help:
                    <div class="toolParamHelp" style="clear: both;">
                        ${param.help}
                    </div>
                %endif
                <div style="clear: both"></div>     
            </div>
        </%def>

        <br/><br/>
        <ul class="manage-table-actions">
            %if webapp == 'galaxy':
                <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
                <div popupmenu="repository-${repository.id}-popup">
                    <li><a class="action-button" href="${h.url_for( controller='repository', action='install_repository_revision', repository_id=trans.security.encode_id( repository.id ), webapp=webapp, changeset_revision=changeset_revision )}">Install to local Galaxy</a></li>
                    <li><a class="action-button" href="${h.url_for( controller='repository', action='preview_tools_in_changeset', repository_id=trans.security.encode_id( repository.id ), webapp=webapp, changeset_revision=changeset_revision )}">Browse repository</a></li>
                </div>
                <li><a class="action-button" id="tool_shed-${repository.id}-popup" class="menubutton">Tool Shed Actions</a></li>
                <div popupmenu="tool_shed-${repository.id}-popup">
                    <a class="action-button" href="${h.url_for( controller='repository', action='browse_valid_repositories', webapp=webapp )}">Browse valid repositories</a>
                    <a class="action-button" href="${h.url_for( controller='repository', action='find_tools', webapp=webapp )}">Search for valid tools</a>
                    <a class="action-button" href="${h.url_for( controller='repository', action='find_workflows', webapp=webapp )}">Search for workflows</a>
                </div>
            %else:
                %if is_new:
                    <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp=webapp )}">Upload files to repository</a>
                %else:
                    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
                    <div popupmenu="repository-${repository.id}-popup">
                        %if can_manage:
                            <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision )}">Manage repository</a>
                        %else:
                            <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, webapp=webapp )}">View repository</a>
                        %endif
                        %if can_upload:
                            <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp=webapp )}">Upload files to repository</a>
                        %endif
                        %if can_view_change_log:
                            <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ), webapp=webapp )}">View change log</a>
                        %endif
                        %if can_browse_contents:
                            <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ), webapp=webapp )}">${browse_label}</a>
                        %endif
                        %if can_rate:
                            <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.app.security.encode_id( repository.id ) )}">Rate repository</a>
                        %endif
                        %if can_contact_owner:
                            <a class="action-button" href="${h.url_for( controller='repository', action='contact_owner', id=trans.security.encode_id( repository.id ), webapp=webapp )}">Contact repository owner</a>
                        %endif
                        %if can_download:
                            <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='gz' )}">Download as a .tar.gz file</a>
                            <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='bz2' )}">Download as a .tar.bz2 file</a>
                            <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='zip' )}">Download as a zip file</a>
                        %endif
                    </div>
                %endif
            %endif
        </ul>
        
        %if message:
            ${render_msg( message, status )}
        %endif

        %if tool:
            <div class="toolForm" id="${tool.id}">
                <div class="toolFormTitle">${tool.name} (version ${tool.version})</div>
                <div class="toolFormBody">
                    <form id="tool_form" name="tool_form" action="" method="get">
                        <input type="hidden" name="tool_state" value="${util.object_to_string( tool_state.encode( tool, app ) )}">
                        ${do_inputs( tool.inputs_by_page[ tool_state.page ], tool_state.inputs, "" )}  
                    </form>
                </div>
            </div>
            %if tool.help:
                <div class="toolHelp">
                    <div class="toolHelpBody">
                        <%
                            # Convert to unicode to display non-ascii characters.
                            if type( tool.help ) is not unicode:
                                tool.help = unicode( tool.help, 'utf-8')
                        %>
                        ${tool.help}
                    </div>        
                </div>
            %endif
        %else:
            Tool not properly loaded.
        %endif
    </body>
</html>
