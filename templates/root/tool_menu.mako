<%inherit file="/base.mako"/>

<%namespace file="/tagging_common.mako" import="render_tool_tagging_elements" />

## Render a workflow
<%def name="render_workflow( key, workflow, section )">
    %if section:
        <div class="toolTitle">
    %else:
        <div class="toolTitleNoSection">
    %endif
        <% encoded_id = key.lstrip( 'workflow_' ) %>
        <a id="link-${workflow.id}" href="${ h.url_for( controller='workflow', action='run', id=encoded_id )}" target="_parent">${_(workflow.name)}</a>
    </div>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.templates( "tool_link", "panel_section", "tool_search" )}
    ${h.js( "galaxy.base", "json2", "autocomplete_tagging", "mvc/tools" )}
    
    <%
        # Set up for creating tool panel.
        tool_search_hidden = "false"
        if trans.user and trans.user.preferences.get( "show_tool_search", "False" ) == "False":
            tool_search_hidden = "true"
        
        dictified_panel = trans.app.toolbox.to_dict( trans )
    %>
    
    <script type="text/javascript">
        // Init. on document load.
        var tool_panel, tool_panel_view, tool_search;
        $(function() {
            // Set up search.
            tool_search = new ToolSearch( {spinner_url: "${h.url_for('/static/images/loading_small_white_bg.gif')}",
                                           search_url: "${h.url_for( controller='root', action='tool_search' )}",
                                           hidden: ${tool_search_hidden} } );
            
            // Set up tool panel.
            tool_panel = new ToolPanel( { tool_search: tool_search } );
            tool_panel.reset( tool_panel.parse( ${h.to_json_string( dictified_panel )} ) );
            
            // Set up tool panel view and initialize.
            tool_panel_view = new ToolPanelView( {collection: tool_panel} );
            tool_panel_view.render();
            $('body').prepend(tool_panel_view.$el);
                        
            // Minsize init hint.
            $( "a[minsizehint]" ).click( function() {
                if ( parent.handle_minwidth_hint ) {
                    parent.handle_minwidth_hint( $(this).attr( "minsizehint" ) );
                }
            });
            
            // Log clicks on tools.
            /*
            $("div.toolTitle > a").click( function() {
                var tool_title = $(this).attr('id').split("-")[1];
                var section_title = $.trim( $(this).parents("div.toolSectionWrapper").find("div.toolSectionTitle").text() );
                var search_active = $(this).parents("div.toolTitle").hasClass("search_match");
                
                // Log action.
                galaxy_async.log_user_action("tool_menu_click." + tool_title, section_title, 
                                                JSON.stringify({"search_active" : search_active}));
            });
            */
            
            // TODO: is this necessary?
            $( "a[minsizehint]" ).click( function() {
                if ( parent.handle_minwidth_hint ) {
                    parent.handle_minwidth_hint( $(this).attr( "minsizehint" ) );
                }
            });
        });
    </script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css("tool_menu")}
</%def>


<%def name="title()">
    ${_('Galaxy Tools')}
</%def>

## Default body
<body class="toolMenuContainer">
    
    <div class="toolMenu">
        ## Feedback when search returns no results.
        <div id="search-no-results" style="display: none; padding-top: 5px">
            <em><strong>Search did not match any tools.</strong></em>
        </div>
        
        ## Link to workflow management. The location of this may change, but eventually
        ## at least some workflows will appear here (the user should be able to
        ## configure which of their stored workflows appear in the tools menu). 
        
        %if t.user:
            <div class="toolSectionPad"></div>
            <div class="toolSectionPad"></div>
            <div class="toolSectionTitle" id="title_XXinternalXXworkflow">
              <span>Workflows</span>
            </div>
            <div id="XXinternalXXworkflow" class="toolSectionBody">
                <div class="toolSectionBg">
                    %if t.user.stored_workflow_menu_entries:
                        %for m in t.user.stored_workflow_menu_entries:
                            <div class="toolTitle">
                                <a href="${h.url_for( controller='workflow', action='run', id=trans.security.encode_id(m.stored_workflow_id) )}" target="galaxy_main">${m.stored_workflow.name}</a>
                            </div>
                        %endfor
                    %endif
                    <div class="toolTitle">
                        <a href="${h.url_for( controller='workflow', action='list_for_run')}" target="galaxy_main">All workflows</a>
                    </div>
                </div>
            </div>
        %endif
        
    </div>
</body>