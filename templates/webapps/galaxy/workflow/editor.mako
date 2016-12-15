<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.active_view="workflow"
    self.overlay_visible=True
    self.editor_config = {
        'id'      : trans.security.encode_id( stored.id ),
        'urls'    : {
            'tool_search'         : h.url_for( '/api/tools' ),
            'get_datatypes'       : h.url_for( '/api/datatypes/mapping' ),
            'load_workflow'       : h.url_for( controller='workflow', action='load_workflow' ),
            'run_workflow'        : h.url_for( controller='root', action='index', workflow_id=trans.security.encode_id(stored.id)),
            'rename_async'        : h.url_for( controller='workflow', action='rename_async', id=trans.security.encode_id(stored.id) ),
            'annotate_async'      : h.url_for( controller='workflow', action='annotate_async', id=trans.security.encode_id(stored.id) ),
            'get_new_module_info' : h.url_for(controller='workflow', action='get_new_module_info' ),
            'workflow_index'      : h.url_for( controller='workflow', action='index' ),
            'save_workflow'       : h.url_for(controller='workflow', action='save_workflow' ),
            'workflow_save_as'    : h.url_for(controller='workflow', action='save_workflow_as') 
        },
        'workflows' : [{
            'id'                  : trans.security.encode_id( workflow.id ),
            'latest_id'           : trans.security.encode_id( workflow.latest_workflow.id ),
            'step_count'          : len( workflow.latest_workflow.steps ),
            'name'                : h.to_unicode( workflow.name )
        } for workflow in workflows ]
    }
%>
</%def>

<%def name="javascripts()">

    ${parent.javascripts()}

    ${h.js(
        "libs/jquery/jquery.event.drag",
        "libs/jquery/jquery.event.drop",
        "libs/jquery/jquery.event.hover",
        "libs/jquery/jquery.form",
        "libs/jquery/jstorage",
        "libs/jquery/jquery.autocomplete",
    )}

    <script type='text/javascript'>
        workflow_view = null;
        $( function() {
            require(['mvc/workflow/workflow-view'], function(Workflow){
                workflow_view = new Workflow(${h.dumps(self.editor_config)});
            });
        });
    </script>
</%def>

<%def name="stylesheets()">

    ## Include "base.css" for styling tool menu and forms (details)
    ${h.css( "base", "autocomplete_tagging", "jquery-ui/smoothness/jquery-ui" )}

    ## But make sure styles for the layout take precedence
    ${parent.stylesheets()}

    <style type="text/css">
    body { margin: 0; padding: 0; overflow: hidden; }

    div.toolTitleDisabled {
        padding-top: 5px;
        padding-bottom: 5px;
        margin-left: 16px;
        margin-right: 10px;
        display: list-item;
        list-style: square outside;
        font-style: italic;
        color: gray;
    }
    div.toolTitleNoSectionDisabled {
      padding-bottom: 0px;
      font-style: italic;
      color: gray;
    }
    div.toolFormRow {
        position: relative;
    }

    .right-content {
        margin: 3px;
    }

    canvas { position: absolute; z-index: 10; }
    canvas.dragging { position: absolute; z-index: 1000; }
    .input-terminal { width: 12px; height: 12px; background: url(${h.url_for('/static/style/workflow_circle_open.png')}); position: absolute; top: 50%; margin-top: -6px; left: -6px; z-index: 1500; }
    .output-terminal { width: 12px; height: 12px; background: url(${h.url_for('/static/style/workflow_circle_open.png')}); position: absolute; top: 50%; margin-top: -6px; right: -6px; z-index: 1500; }
    .drag-terminal { width: 12px; height: 12px; background: url(${h.url_for('/static/style/workflow_circle_drag.png')}); position: absolute; z-index: 1500; }
    .input-terminal-active { background: url(${h.url_for('/static/style/workflow_circle_green.png')}); }
    ## .input-terminal-hover { background: yellow; border: solid black 1px; }
    .unselectable { -moz-user-select: none; -khtml-user-select: none; user-select: none; }
    img { border: 0; }

    div.buttons img {
    width: 16px; height: 16px;
    cursor: pointer;
    }

    ## Extra styles for the representation of a tool on the canvas (looks like
    ## a tiny tool form)
    div.toolFormInCanvas {
        z-index: 100;
        position: absolute;
        ## min-width: 130px;
        margin: 6px;
    }

    div.toolForm-active {
        z-index: 1001;
        border: solid #8080FF 4px;
        margin: 3px;
    }

    div.toolFormTitle {
        cursor: move;
        min-height: 16px;
    }

    div.titleRow {
        font-weight: bold;
        border-bottom: dotted gray 1px;
        margin-bottom: 0.5em;
        padding-bottom: 0.25em;
    }
    div.form-row {
      position: relative;
    }

    div.tool-node-error div.toolFormTitle {
        background: #FFCCCC;
        border-color: #AA6666;
    }
    div.tool-node-error {
        border-color: #AA6666;
    }

    #canvas-area {
        position: absolute;
        top: 0; left: 305px; bottom: 0; right: 0;
        border: solid red 1px;
        overflow: none;
    }

    .form-row {
    }

    div.toolFormInCanvas div.toolFormBody {
        padding: 0;
    }
    .form-row-clear {
        clear: both;
    }

    div.rule {
        height: 0;
        border: none;
        border-bottom: dotted black 1px;
        margin: 0 5px;
    }

    .callout {
        position: absolute;
        z-index: 10000;
    }

    .pjaForm {
        margin-bottom:10px;
    }

    .pjaForm .toolFormBody{
        padding:10px;
    }

    .pjaForm .toolParamHelp{
        padding:5px;
    }

    .panel-header-button-group {
        margin-right: 5px;
        padding-right: 5px;
        border-right: solid gray 1px;
    }

    </style>
</%def>

## Render a tool in the tool panel
<%def name="render_tool( tool, section )">
    %if not tool.hidden:
        %if tool.is_workflow_compatible:
            %if section:
                <div class="toolTitle">
            %else:
                <div class="toolTitleNoSection">
            %endif
                %if "[[" in tool.description and "]]" in tool.description:
                    ${tool.description.replace( '[[', '<a id="link-${tool.id}" href="workflow_view.add_node_for_tool( ${tool.id} )">' % tool.id ).replace( "]]", "</a>" )}
                %elif tool.name:
                    <a id="link-${tool.id}" href="#" onclick="workflow_view.add_node_for_tool( '${tool.id}', '${tool.name}' )">${tool.name}</a> ${tool.description}
                %else:
                    <a id="link-${tool.id}" href="#" onclick="workflow_view.add_node_for_tool( '${tool.id}', '${tool.name}' )">${tool.description}</a>
                %endif
            </div>
        %else:
            %if section:
                <div class="toolTitleDisabled">
            %else:
                <div class="toolTitleNoSectionDisabled">
            %endif
                %if "[[" in tool.description and "]]" in tool.description:
                    ${tool.description.replace( '[[', '' % tool.id ).replace( "]]", "" )}
                %elif tool.name:
                    ${tool.name} ${tool.description}
                %else:
                    ${tool.description}
                %endif
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
    <div class="toolSectionTitle" id="title___workflow__${module_section['name']}__">
        <span>${module_section["title"]}</span>
    </div>
    <div id="__workflow__${module_section['name']}__" class="toolSectionBody">
        <div class="toolSectionBg">
            %for module in module_section["modules"]:
                <div class="toolTitle">
                    <a href="#" onclick="workflow_view.add_node_for_module( '${module['name']}', '${module['title']}' )">
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

    <div class="unified-panel-body" style="overflow: auto;">
        <div class="toolMenuContainer">
            <div class="toolMenu">
                <%
                    from galaxy.workflow.modules import load_module_sections
                    module_sections = load_module_sections( trans )
                %>
                %if trans.app.config.message_box_visible:
                    <div id="tool-search" style="top: 95px;">
                %else:
                    <div id="tool-search">
                %endif
                    <input type="text" name="query" placeholder="search tools" id="tool-search-query" class="search-query parent-width" />
                    <img src="${h.url_for('/static/images/loading_small_white_bg.gif')}" id="search-spinner" class="search-spinner" />
                </div>

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
                            <div class="toolSectionTitle" id="title_${section.id}">
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
                    %if trans.user_is_admin() and trans.app.data_managers.data_managers:
                       <div>&nbsp;</div>
                       <div class="toolSectionWrapper">
                           <div class="toolSectionTitle" id="title___DATA_MANAGER_TOOLS__">
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

    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner" style="float: right">
            <a id="workflow-options-button" class="panel-header-button" href="#"><span class="fa fa-cog"></span></a>
        </div>
        <div class="unified-panel-header-inner">
            Workflow Canvas | ${h.to_unicode( stored.name ) | h}
        </div>
    </div>
    <div class="unified-panel-body">
        <div id="canvas-viewport" style="width: 100%; height: 100%; position: absolute; overflow: hidden; background: #EEEEEE; background: white url(${h.url_for('/static/images/light_gray_grid.gif')}) repeat;">
            <div id="canvas-container" style="position: absolute; width: 100%; height: 100%;"></div>
        </div>
        <div id="overview-border" style="position: absolute; width: 150px; height: 150px; right: 20000px; bottom: 0px; border-top: solid gray 1px; border-left: solid grey 1px; padding: 7px 0 0 7px; background: #EEEEEE no-repeat url(${h.url_for('/static/images/resizable.png')}); z-index: 20000; overflow: hidden; max-width: 300px; max-height: 300px; min-width: 50px; min-height: 50px">
            <div style="position: relative; overflow: hidden; width: 100%; height: 100%; border-top: solid gray 1px; border-left: solid grey 1px;">
                <div id="overview" style="position: absolute;">
                    <canvas width="0" height="0" style="background: white; width: 100%; height: 100%;" id="overview-canvas"></canvas>
                    <div id="overview-viewport" style="position: absolute; width: 0px; height: 0px; border: solid blue 1px; z-index: 10;"></div>
                </div>
            </div>
        </div>
        <div id='workflow-parameters-box' style="display:none; position: absolute; /*width: 150px; height: 150px;*/ right: 0px; top: 0px; border-bottom: solid gray 1px; border-left: solid grey 1px; padding: 7px; background: #EEEEEE; z-index: 20000; overflow: hidden; max-width: 300px; max-height: 300px; /*min-width: 50px; min-height: 50px*/">
            <div style="margin-bottom:5px;"><b>Workflow Parameters</b></div>
            <div id="workflow-parameters-container">
            </div>
        </div>
        <div id="close-viewport" style="border-left: 1px solid #999; border-top: 1px solid #999; background: #ddd url(${h.url_for('/static/images/overview_arrows.png')}) 12px 0px; position: absolute; right: 0px; bottom: 0px; width: 12px; height: 12px; z-index: 25000;"></div>
    </div>

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
            ## Workflow tags.
            <%namespace file="/tagging_common.mako" import="render_individual_tagging_element" />
            <div class="form-row">
                <label>
                    Tags:
                </label>
                    <div style="float: left; width: 225px; margin-right: 10px; border-style: inset; border-width: 1px; margin-left: 2px">
                        <style>
                            .tag-area {
                                border: none;
                            }
                        </style>
                        ${render_individual_tagging_element(user=trans.get_user(), tagged_item=stored, elt_context="edit_attributes.mako", use_toggle_link=False, input_size="20")}
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
