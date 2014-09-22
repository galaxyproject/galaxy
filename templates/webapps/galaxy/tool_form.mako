<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/base_panels.mako" import="overlay" />

<% import galaxy.util %>

<%def name="stylesheets()">
    ${h.css( "autocomplete_tagging", "base", "library" )}
    <style type="text/css">
        html, body {
            background-color: #fff;
        }
    </style>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "galaxy.panels", "libs/jquery/jstorage" )}
    ${h.js( "libs/bibtex" )}
    <script type="text/javascript">
        require( [ "galaxy.tools" ] );
        window.enhanced_galaxy_tools = true;
    </script>
    <script type="text/javascript">
    $(function() {
        $(window).bind("refresh_on_change", function() {
            $(':file').each( function() {
                var file = $(this);
                var file_value = file.val();
                if (file_value) {
                    // disable file input, since we don't want to upload the file on refresh
                    var file_name = $(this).attr("name");
                    file.attr( { name: 'replaced_file_input_' + file_name, disabled: true } );
                    // create a new hidden field which stores the filename and has the original name of the file input
                    var new_file_input = $(document.createElement('input'));
                    new_file_input.attr( { "type": "hidden", "value": file_value, "name": file_name } );
                    file.after(new_file_input);
                }
            });
        });

        // For drilldown parameters: add expand/collapse buttons and collapse initially-collapsed elements
        $( 'div.drilldown-container' ).each( function() {
            $(this).find('span.form-toggle' ).each( function() {
                var show_hide_click_elt = $(this);
                var group_id = show_hide_click_elt.attr('id').substring( 0, show_hide_click_elt.attr('id').lastIndexOf( '-click' ) );
                $('#' + group_id + '-container').each( function() {
                    var show_hide_elt = $(this);
                    if (  show_hide_click_elt.hasClass( 'toggle-expand' ) ) {
                        show_hide_elt.hide();
                    }
                    show_hide_click_elt.click( function() {
                        if ( show_hide_click_elt.hasClass("toggle") ){
                            show_hide_click_elt.addClass("toggle-expand");
                            show_hide_click_elt.removeClass("toggle");
                            show_hide_elt.slideUp( 'fast' );
                        }
                        else {
                            show_hide_click_elt.addClass("toggle");
                            show_hide_click_elt.removeClass("toggle-expand");
                            show_hide_elt.slideDown( 'fast' );
                        }
                    });
                });
            });
        });

        $(".add-librarydataset").click(function() {
            var link = $(this);
            $.ajax({
                url: "/visualization/list_libraries",
                error: function(xhr, ajaxOptions, thrownError) { alert( "Grid failed" ); console.log(xhr, ajaxOptions, thrownError); },
                success: function(table_html) {
                    show_modal(
                        "Select Library Dataset",
                        table_html, {
                            "Cancel": function() {
                                hide_modal();
                            },
                            "Select": function() {
                                var names = [];
                                var ids = [];
                                counter = 1;
                                $('input[name=ldda_ids]:checked').each(function() {
                                    var name = $.trim( $(this).siblings("label").text() );
                                    var id = $(this).val();
                                    names.push( counter + ". " + name );
                                    counter += 1;
                                    ids.push(id);
                                });
                                link.html( names.join("<br/>") );
                                link.siblings("input[type=hidden]").val( ids.join("||") );
                                hide_modal();
                            }
                        }
                    );
                }
            });
        });
    });

    %if not add_frame.debug:
        if( window.name != "galaxy_main" ) {
            location.replace( '${h.url_for( controller='root', action='index', tool_id=tool.id )}' );
        }
    %endif

    </script>

</%def>

<%def name="do_inputs( inputs, tool_state, errors, prefix, other_values=None )">
    <%
    from galaxy.util.expressions import ExpressionContext
    other_values = ExpressionContext( tool_state, other_values )
    %>
    %for input_index, input in enumerate( inputs.itervalues() ):
        %if not input.visible:
            <% pass %>
        %elif input.type == "repeat":
          <div class="repeat-group">
              <div class="form-title-row"><strong>${input.title_plural}</strong>
              %if input.help:
                  <div class="toolParamHelp" style="clear: both;">
                      ${input.help}
                  </div>
              %endif
              </div>
              <%
              repeat_state = tool_state[input.name]
              num_repeats = len( repeat_state )
              %>
              %for i in range( num_repeats ):
                <div class="repeat-group-item">
                    <%
                    if input.name in errors:
                        rep_errors = errors[input.name][i]
                    else:
                        rep_errors = dict()
                    index = repeat_state[i]['__index__']
                    %>
                    <div class="form-title-row"><strong>${input.title} ${i + 1}</strong></div>
                    ${do_inputs( input.inputs, repeat_state[i], rep_errors, prefix + input.name + "_" + str(index) + "|", other_values )}
                    %if input.min < num_repeats:
                        <div class="form-row"><input type="submit" class="btn" name="${prefix}${input.name}_${index}_remove" value="Remove ${input.title} ${i+1}"></div>
                    %endif
                </div>
                %if rep_errors.has_key( '__index__' ):
                    <div><img style="vertical-align: middle;" src="${h.url_for('/static/style/error_small.png')}">&nbsp;<span style="vertical-align: middle;">${rep_errors['__index__']}</span></div>
                %endif
              %endfor
              %if input.max > num_repeats:
                  <div class="form-row"><input type="submit" class="btn" name="${prefix}${input.name}_add" value="Add new ${input.title}"></div>
              %endif
          </div>
        %elif input.type == "conditional":
            <%
            group_state = tool_state[input.name]
            group_errors = errors.get( input.name, {} )
            current_case = group_state['__current_case__']
            group_prefix = prefix + input.name + "|"
            %>
            %if input.value_ref_in_group:
                ${row_for_param( group_prefix, input.test_param, group_state, group_errors, other_values )}
            %endif
            ${do_inputs( input.cases[current_case].inputs, group_state, group_errors, group_prefix, other_values )}
        %elif input.type == "upload_dataset":
            %if input.get_datatype( trans, other_values ).composite_type is None: #have non-composite upload appear as before
                <%
                if input.name in errors:
                    rep_errors = errors[input.name][0]
                else:
                    rep_errors = dict()
                %>
              ${do_inputs( input.inputs, tool_state[input.name][0], rep_errors, prefix + input.name + "_" + str( 0 ) + "|", other_values )}
            %else:
                <div class="repeat-group">
                    <div class="form-title-row"><strong>${input.group_title( other_values )}</strong></div>
                    <%
                    repeat_state = tool_state[input.name]
                    %>
                    %for i in range( len( repeat_state ) ):
                      <div class="repeat-group-item">
                      <%
                      if input.name in errors:
                          rep_errors = errors[input.name][i]
                      else:
                          rep_errors = dict()
                      index = repeat_state[i]['__index__']
                      %>
                      <div class="form-title-row"><strong>File Contents for ${input.title_by_index( trans, i, other_values )}</strong></div>
                      ${do_inputs( input.inputs, repeat_state[i], rep_errors, prefix + input.name + "_" + str(index) + "|", other_values )}
                      ##<div class="form-row"><input type="submit" name="${prefix}${input.name}_${index}_remove" value="Remove ${input.title} ${i+1}"></div>
                      </div>
                    %endfor
                    ##<div class="form-row"><input type="submit" name="${prefix}${input.name}_add" value="Add new ${input.title}"></div>
                </div>
            %endif
        %else:
            ${row_for_param( prefix, input, tool_state, errors, other_values )}
        %endif
    %endfor
</%def>

<%def name="row_for_param( prefix, param, parent_state, parent_errors, other_values )">
    <%
    if parent_errors.has_key( param.name ):
        cls = "form-row form-row-error"
    else:
        cls = "form-row"

    field = param.get_html_field( trans, parent_state[ param.name ], other_values )
    field.refresh_on_change = param.refresh_on_change

    # Field may contain characters submitted by user and these characters may
    # be unicode; handle non-ascii characters gracefully.
    field_html = field.get_html( prefix )
    if type( field_html ) is not unicode:
        field_html = unicode( field_html, 'utf-8', 'replace' )

    if param.type == "hidden":
        return field_html
    %>
    <div class="${cls}">
        ${label_for_param( param )}
        ${input_for_param( param, field_html )}
        ${errors_for_param( param, parent_errors )}
        ${help_for_param( param )}
        <div style="clear: both;"></div>
    </div>
</%def>

<%def name="input_for_param( param, field_html )">
    <div class="form-row-input">${field_html}</div>
</%def>

<%def name="label_for_param( param )">
    <% label = param.get_label()%>
    %if label:
        <label for="${param.name}">${label}:</label>
    %endif
</%def>

<%def name="errors_for_param( param, parent_errors )">
    %if parent_errors.has_key( param.name ):
        <div class="form-row-error-message">
            <div><img style="vertical-align: middle;" src="${h.url_for('/static/style/error_small.png')}">&nbsp;<span style="vertical-align: middle;">${parent_errors[param.name]}</span></div>
        </div>
    %endif
</%def>

<%def name="help_for_param( param )">
    %if param.help:
        <div class="toolParamHelp" style="clear: both;">
            ${param.help}
        </div>
    %endif
</%def>

<%def name="row_for_rerun()">
    %if trans.app.config.track_jobs_in_database and tool_state.rerun_remap_job_id is not None:
        <div id="remap-row" class="form-row">
            <input type="checkbox" name="rerun_remap_job_id" value="${tool_state.rerun_remap_job_id}"> Resume dependencies from this job
            <div class="toolParamHelp" style="clear: both;">
                The previous run of this tool failed and other tools were waiting for it to finish successfully, use this option to resume those tools using the outputs of this tool run.
            </div>
        </div>
        <div style="clear: both;"></div>
    %endif
</%def>

<% overlay(visible=False) %>

%if add_frame.from_noframe:
    <div class="warningmessage">
        <strong>Welcome to Galaxy</strong>
        <hr/>
        It appears that you found this tool from a link outside of Galaxy.
        If you're not familiar with Galaxy, please consider visiting the
        <a href="${h.url_for( controller='root' )}" target="_top">welcome page</a>.
        To learn more about what Galaxy is and what it can do for you, please visit
        the <a href="${add_frame.wiki_url}" target="_top">Galaxy wiki</a>.
    </div>
    <br/>
%endif

<%
    # Render an error message if a dynamically generated select list is missing a required
    # index file or entry in the tool_data_table_conf.xml file.
    message = ""
    params_with_missing_data_table_entry = tool.params_with_missing_data_table_entry
    params_with_missing_index_file = tool.params_with_missing_index_file
    if params_with_missing_data_table_entry:
        param = params_with_missing_data_table_entry[0]
        message += "Data table named '%s' is required by tool but not configured.  " % param.options.missing_tool_data_table_name
    if tool.params_with_missing_index_file:
        param = params_with_missing_index_file[0]
        message += "Index file named '%s' is required by tool but not available.  " % param.options.missing_index_file

    # Handle calculating the redirect url for the special case where we have nginx proxy
    # upload and need to do url_for on the redirect portion of the tool action.
    try:
        tool_url = h.url_for(tool.action)
    except AttributeError:
        assert len(tool.action) == 2
        tool_url = tool.action[0] + h.url_for(tool.action[1])
%>

<%
    # Name of the tool in lower case
    low_tool_name = tool.name.lower()
%>

%if tool_id_version_message:
    ${render_msg( tool_id_version_message, 'warning' )}
%endif

<div class="toolForm" id="${tool.id}">
    <form id="tool_form" name="tool_form" action="${tool_url}" enctype="${tool.enctype}" target="${tool.target}" method="${tool.method}">
        %if tool.has_multiple_pages:
            <div class="toolFormTitle">${tool.name} (step ${tool_state.page+1} of ${tool.npages})
        %elif not tool_version_select_field:
            <div class="toolFormTitle">${tool.name} (version ${tool.version})
        %else:
            <div class="toolFormTitle">${tool.name} ${tool_version_select_field.get_html()}
        %endif

        <span class="pull-right">
        %if trans.app.config.biostar_url:
                ## BioStar links
                Help from Biostar
                <div class="icon-btn-group">
                    <a href="${h.url_for( controller='biostar', action='biostar_tool_tag_redirect', tool_id=tool.id )}"
                        target="_blank" class="icon-btn" title="Search for this tool" data-toggle="tooltip" data-placement="bottom"><span class="fa fa-search"></span></a>
                    <a href="${h.url_for( controller='biostar', action='biostar_tool_question_redirect', tool_id=tool.id )}"
                        target="_blank" class="icon-btn" title="Ask a question about this tool" data-toggle="tooltip" data-placement="bottom"><span class="fa fa-question-circle"></a>
                </div>
        %endif
            <div class="icon-btn-group">
                <a href="#" data-link="${h.url_for( controller='root', action='index', tool_id=tool.id )}"
                    class="icon-btn tool-share-link" title="Share this tool" data-toggle="tooltip" data-placement="bottom"><span class="fa fa-share"></span></a>
            </div>
        </span>
        </div>
        <div class="toolFormBody">
            <input type="hidden" name="refresh" value="refresh">
            <input type="hidden" name="tool_id" value="${tool.id}">
            <input type="hidden" name="tool_state" value="${util.object_to_string( tool_state.encode( tool, app ) )}">
            %if tool.display_by_page[tool_state.page]:
                ${trans.fill_template_string( tool.display_by_page[tool_state.page], context=tool.get_param_html_map( trans, tool_state.page, tool_state.inputs ) )}
                ${row_for_rerun()}
                <input type="submit" class="btn btn-primary" name="runtool_btn" value="Execute">
            %else:
                ${do_inputs( tool.inputs_by_page[ tool_state.page ], tool_state.inputs, errors, "" )}
                %if tool_state.page == tool.last_page:
                    ${row_for_rerun()}
                %endif
                <div class="form-row form-actions">
                    %if tool_state.page == tool.last_page:
                        <input type="submit" class="btn btn-primary" name="runtool_btn" value="Execute">
                    %else:
                        <input type="submit" class="btn btn-primary" name="runtool_btn" value="Next step">
                    %endif
                </div>
            %endif
        </div>
    </form>
</div>
%if tool.help:
    <div class="toolHelp">
        <div class="toolHelpBody">
            <%
                if tool.has_multiple_pages:
                    tool_help = tool.help_by_page[tool_state.page]
                else:
                    tool_help = tool.help

                # Help is Mako template, so render using current static path.
                tool_help = tool_help.render( static_path=h.url_for( '/static' ), host_url=h.url_for('/', qualified=True) )

                # Convert to unicode to display non-ascii characters.
                if type( tool_help ) is not unicode:
                    tool_help = unicode( tool_help, 'utf-8')
            %>
            ${tool_help}
        </div>
    </div>
%endif
%if tool.tool_shed_repository:
    <% tool_url = tool.tool_shed_repository.get_sharable_url( tool.app ) %>
    %if tool_url:
        <br/>
        ${ render_msg( 'This tool was installed from a ToolShed, you may be able to find additional information by following this link: <a href="%s" target="_blank">%s</a>' % ( tool_url, tool_url ), 'info' ) }
    %endif
%endif
%if tool.citations:
    <script>
    require(["mvc/citation/citation-model", "mvc/citation/citation-view"
    ], function( citationModel, citationView ){
        $(function() {
            var citations = new citationModel.ToolCitationCollection();
            citations.tool_id = "${tool.id}";
            var citation_list_view = new citationView.CitationListView({ collection: citations } );
            citation_list_view.render();
            citations.fetch();
        } );
    } );
    </script>
    <div id="citations">
    </div>
%endif

