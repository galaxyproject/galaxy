<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="title()">
    Workflow Editor
</%def>

<%def name="init()">
<%
    self.active_view="workflow"
    self.overlay_visible=True
%>
</%def>

<%def name="javascript_app()">

    ${parent.javascript_app()}

    <script type="text/javascript">
        var editorConfig = ${ h.dumps( editor_config ) };
        config.addInitialization(function(galaxy, config) {
            console.log("workflow/editor.mako, editorConfig", editorConfig);
            window.bundleEntries.mountWorkflowEditor(editorConfig);
            window.bundleEntries.mountToolBoxWorkflow(editorConfig);
        });
    </script>

</%def>

<%def name="stylesheets()">
    ## Include "base.css" for styling tool menu and forms (details)
    ${h.css("jquery-ui/smoothness/jquery-ui" )}

    ## But make sure styles for the layout take precedence
    ${parent.stylesheets()}
</%def>

## Render a tool in the tool panel
<%def name="render_tool( tool, section )">
    <%
        import markupsafe
    %>
    %if not tool.hidden:
        %if tool.is_workflow_compatible:
            %if section:
                <div class="toolTitle">
            %else:
                <div class="toolTitleNoSection">
            %endif
                %if "[[" in tool.description and "]]" in tool.description:
                    ${tool.description.replace( '[[', '<a id="link-${tool.id}" href="workflow_globals.app.add_node_for_tool( ${tool.id} )">' % tool.id ).replace( "]]", "</a>" )}
                %elif tool.name:
                    <a id="link-${tool.id}" role="button" href="javascript:void(0)" onclick="workflow_globals.app.add_node_for_tool( '${tool.id}', '${markupsafe.escape( tool.name ) | h}' )" style="text-decoration: none; display: block;"><span style="text-decoration: underline">${tool.name | h}</span> ${tool.description}</a>
                %else:
                    <a id="link-${tool.id}" role="button" href="javascript:void(0)" onclick="workflow_globals.app.add_node_for_tool( '${tool.id}', '${markupsafe.escape( tool.name ) | h}' )">${tool.description}</a>
                %endif
            </div>
        %else:
            %if section:
                <div class="toolTitle text-muted">
            %else:
                <div class="toolTitleNoSection text-muted">
            %endif
	        <a>
		    %if "[[" in tool.description and "]]" in tool.description:
                        ${tool.description.replace( '[[', '' % tool.id ).replace( "]]", "" )}
                    %elif tool.name:
                        ${tool.name} ${tool.description}
                    %else:
                        ${tool.description}
                    %endif
		</a>
            </div>
        %endif
    %endif
</%def>

## Render a label in the tool panel
<%def name="render_label( label )">
    <div class="toolPanelLabel" id="title_${label.id}">
        <span>${label.text}</span>
    </div>
</%def>

<%def name="overlay(visible=False)">
    ${parent.overlay( "Loading workflow editor...",
                      "<div class='progress progress-striped progress-info active'><div class='progress-bar' style='width: 100%;'></div></div>", self.overlay_visible )}
</%def>


<%def name="render_module_section(module_section)">
    <div class="toolSectionTitle" role="button" id="title___workflow__${module_section['name']}__">
        <span>${module_section["title"]}</span>
    </div>
    <div id="__workflow__${module_section['name']}__" class="toolSectionBody">
        <div class="toolSectionBg">
            %for module in module_section["modules"]:
                <div class="toolTitle">
                    <a role="button" href="javascript:void(0)" id="tool-menu-${module_section['name']}-${module['name']}" onclick="workflow_globals.app.add_node_for_module( '${module['name']}', '${module['title']}' )">
                        ${module['description']}
                    </a>
                </div>
            %endfor
        </div>
    </div>
</%def>

<%def name="left_panel()">
    <%
       from galaxy.tools import Tool
       from galaxy.tools.toolbox import ToolSection, ToolSectionLabel
    %>

    <div class="unified-panel-header" unselectable="on">
        <div class='unified-panel-header-inner'>
            ${n_('Tools')}
        </div>
    </div>

    <div class="unified-panel-controls">
        <div id="tool-search" class="search-input">
            <input id="tool-search-query" class="search-query parent-width" name="query" placeholder="search tools" autocomplete="off" type="text">
            <span id="search-clear-btn" aria-label="clear search" role="button" class="search-clear fa fa-times-circle" title="" data-original-title="clear search (esc)" />
            <span id="search-spinner" class="search-loading fa fa-spinner fa-spin" />
        </div>
    </div>

    <div class="unified-panel-body" style="overflow: auto;">
        <div class="toolMenuContainer">
            <div class="toolMenu" id="workflow-tool-menu">
                <%
                    from galaxy.workflow.modules import load_module_sections
                    module_sections = load_module_sections( trans )
                %>
                <div class="toolSectionWrapper">
                    ${render_module_section(module_sections['inputs'])}
                </div>

                <div class="toolSectionList">
                    %for val in app.toolbox.tool_panel_contents( trans ):
                        <div class="toolSectionWrapper">
                        %if isinstance( val, Tool ):
                            ${render_tool( val, False )}
                        %elif isinstance( val, ToolSection ) and val.elems:
                        <% section = val %>
                            <div class="toolSectionTitle" role="button" id="title_${section.id}">
                                <span>${section.name}</span>
                            </div>
                            <div id="${section.id}" class="toolSectionBody">
                                <div class="toolSectionBg">
                                    %for section_key, section_val in section.elems.items():
                                        %if isinstance( section_val, Tool ):
                                            ${render_tool( section_val, True )}
                                        %elif isinstance( section_val, ToolSectionLabel ):
                                            ${render_label( section_val )}
                                        %endif
                                    %endfor
                                </div>
                            </div>
                        %elif isinstance( val, ToolSectionLabel ):
                            ${render_label( val )}
                        %endif
                        </div>
                    %endfor
                    ## Data Manager Tools
                    %if trans.user_is_admin and trans.app.data_managers.data_managers:
                       <div>&nbsp;</div>
                       <div class="toolSectionWrapper">
                           <div class="toolSectionTitle" role="button" id="title___DATA_MANAGER_TOOLS__">
                               <span>Data Manager Tools</span>
                           </div>
                           <div id="__DATA_MANAGER_TOOLS__" class="toolSectionBody">
                               <div class="toolSectionBg">
                                   %for data_manager_id, data_manager_val in trans.app.data_managers.data_managers.items():
                                       ${ render_tool( data_manager_val.tool, True ) }
                                   %endfor
                               </div>
                           </div>
                       </div>
                    %endif
                    ## End Data Manager Tools
                </div>
                <div>&nbsp;</div>
                %for section_name, module_section in module_sections.items():
                    %if section_name != "inputs":
                        ${render_module_section(module_section)}
                    %endif
                %endfor

                ## Feedback when search returns no results.
                <div id="search-no-results" style="display: none; padding-top: 5px">
                    <em><strong>Search did not match any tools.</strong></em>
                </div>

            </div>
        </div>
    </div>
</%def>

<%def name="center_panel()">
</%def>

<%def name="right_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            Details
        </div>
    </div>
    <div class="unified-panel-body workflow-right" style="overflow: auto;">
        ## Div for elements to modify workflow attributes.
        <div id="edit-attributes" class="metadataForm right-content">
            <div class="metadataFormTitle">Edit Workflow Attributes</div>
            <div class="metadataFormBody">
            ## Workflow name.
            <div id="workflow-name-area" class="form-row">
                <label>Name:</label>
                <span id="workflow-name" class="editable-text" title="Click to rename workflow">${h.to_unicode( stored.name ) | h}</span>
            </div>
            <div id="workflow-version-area" class="form-row">
                <label>Version:</label>
            </div>
            <select id="workflow-version-switch">Select version</select>
            ## Workflow tags.
            <%namespace file="/tagging_common.mako" import="render_individual_tagging_element" />
            <div class="form-row">
                <label>
                    Tags:
                </label>
                    <div style="float: left; width: 225px; margin-right: 10px; border-style: inset; border-width: 1px; margin-left: 2px">
                        ${render_individual_tagging_element(user=trans.get_user(), tagged_item=stored, elt_context="edit_attributes.mako", use_toggle_link=False)}
                    </div>
                    <div class="toolParamHelp">Apply tags to make it easy to search for and find items with the same tag.</div>
                </div>
                ## Workflow annotation.
                ## Annotation elt.
                <div id="workflow-annotation-area" class="form-row">
                    <label>Annotation / Notes:</label>
                    <div id="workflow-annotation" class="editable-text" title="Click to edit annotation">
                    %if annotation:
                        ${h.to_unicode( annotation ) | h}
                    %else:
                        <em>Describe or add notes to workflow</em>
                    %endif
                    </div>
                    <div class="toolParamHelp">Add an annotation or notes to a workflow; annotations are available when a workflow is viewed.</div>
                </div>
            </div>
        </div>

        ## Div where tool details are loaded and modified.
        <div id="right-content" class="right-content"></div>

        ## Workflow output tagging
        <div style="display:none;" id="workflow-output-area" class="metadataForm right-content">
            <div class="metadataFormTitle">Edit Workflow Outputs</div>
            <div class="metadataFormBody"><div class="form-row">
                <div class="toolParamHelp">Tag step outputs to indicate the final dataset(s) to be generated by running this workflow.</div>
                <div id="output-fill-area"></div>
            </div></div>
        </div>

    </div>
</%def>
