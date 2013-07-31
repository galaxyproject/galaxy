<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="*" />

<%
    from galaxy.util.expressions import ExpressionContext
    from galaxy import util
    from galaxy.tools.parameters.basic import DataToolParameter, ColumnListParameter, GenomeBuildParameter, SelectToolParameter
    from galaxy.web.form_builder import SelectField
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
                            try:
                                group_state = tool_state[ input.name ][ 0 ]
                            except Exception, e:
                                group_state = tool_state[ input.name ]
                            current_case = group_state[ '__current_case__' ]
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
                # Disable refresh_on_change for select lists displayed in the tool shed. 
                param.refresh_on_change = False
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

        %if render_repository_actions_for == 'galaxy':
            ${render_galaxy_repository_actions( repository=repository )}
        %else:
            ${render_tool_shed_repository_actions( repository, metadata=None, changeset_revision=None )}
        %endif

        %if message:
            ${render_msg( message, status )}
        %endif

        %if tool:
            <div class="toolForm" id="${tool.id | h}">
                <div class="toolFormTitle">${tool.name | h} (version ${tool.version | h})</div>
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
                            tool_help = tool.help
                            # Help is Mako template, so render using current static path.
                            tool_help = tool_help.render( static_path=h.url_for( '/static' ) )
                            # Convert to unicode to display non-ascii characters.
                            if type( tool_help ) is not unicode:
                                tool_help = unicode( tool_help, 'utf-8')
                        %>
                        ${tool_help}
                    </div>
                </div>
            %endif
        %else:
            Tool not properly loaded.
        %endif
    </body>
</html>
