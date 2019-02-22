import Backbone from "backbone";
import $ from "jquery";
import Tools from "mvc/tool/tools";
import Upload from "mvc/upload/upload-view";
import _l from "utils/localization";
// import ToolForm from "mvc/tool/tool-form-composite";
import _ from "libs/underscore";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import Buttons from "mvc/ui/ui-buttons";

var ToolPanel = Backbone.View.extend({
    initialize: function(page, options) {
        let Galaxy = getGalaxyInstance();
        let appRoot = getAppRoot();

        // access configuration options
        var config = options.config;
        this.root = options.root;

        /** @type {Object[]} descriptions of user's workflows to be shown in the tool menu */
        this.stored_workflow_menu_entries = config.stored_workflow_menu_entries || [];

        // create tool search, tool panel, and tool panel view.
        var tool_search = new Tools.ToolSearch({
            hidden: false
        });
        var tools = new Tools.ToolCollection(config.toolbox);
        this.tool_panel = new Tools.ToolPanel({
            tool_search: tool_search,
            tools: tools,
            layout: config.toolbox_in_panel
        });
        this.tool_panel_view = new Tools.ToolPanelView({
            model: this.tool_panel
        });

        // add upload modal
        this.upload_button = new Upload({
            upload_path: config.nginx_upload_path || `${appRoot}api/tools`,
            chunk_upload_size: config.chunk_upload_size,
            ftp_upload_site: config.ftp_upload_site,
            default_genome: config.default_genome,
            default_extension: config.default_extension
        });

        // add favorite filter button
        this.favorite_button = new Buttons.ButtonLink({
            cls: "panel-header-button",
            title: _l("Show favorites"),
            icon: "fa fa-star-o",
            onclick: e => {
                $("#tool-search-query")
                    .val("#favorites")
                    .trigger("change");
            }
        });

        // add uploader button to Galaxy object
        Galaxy.upload = this.upload_button;

        // components for panel definition
        this.model = new Backbone.Model({
            title: _l("Tools"),
            buttons: [this.upload_button, this.favorite_button]
        });

        // build body template
        this.setElement(this._template());
    },

    render: function() {
        // if there are tools, render panel and display everything
        var self = this;
        if (this.tool_panel.get("layout").size() > 0) {
            this.$el.find(".toolMenu").replaceWith(this.tool_panel_view.$el);
            this.tool_panel_view.render();
        }
        // build the dom for the workflow portion of the tool menu
        // add internal workflow list
        self.$("#internal-workflows").append(
            self._templateAllWorkflow({
                title: _l("All workflows"),
                href: "workflows/list"
            })
        );
        _.each(this.stored_workflow_menu_entries, menu_entry => {
            self.$("#internal-workflows").append(
                self._templateWorkflowLink({
                    title: menu_entry.stored_workflow.name,
                    href: `workflows/run?id=${menu_entry.encoded_stored_workflow_id}`
                })
            );
        });
    },

    /** build a link to one tool */
    _templateTool: function(tool) {
        let appRoot = getAppRoot();
        return `<div class="toolTitle">
                    <a href="${appRoot}${tool.href}" target="galaxy_main">
                        ${tool.title}
                    </a>
                </div>`;
    },

    /** build a link to 'All Workflows' */
    _templateAllWorkflow: function(tool) {
        let appRoot = getAppRoot();
        return `<div class="toolTitle">
                    <a href="${appRoot}${tool.href}">
                        ${tool.title}
                    </a>
                </div>`;
    },

    /** build links to workflows in toolpanel */
    _templateWorkflowLink: function(wf) {
        let appRoot = getAppRoot();
        return `<div class="toolTitle">
                    <a class="${wf.cls}" href="${appRoot}${wf.href}">
                        ${_.escape(wf.title)}
                    </a>
                </div>`;
    },

    /** override to include inital menu dom and workflow section */
    _template: function() {
        return `<div class="toolMenuContainer">
                    <div class="toolMenu" style="display: none">
                        <div id="search-no-results" style="display: none; padding-top: 5px">
                            <em>
                                <strong>
                                    ${_l("Search did not match any tools.")}
                                </strong>
                            </em>
                        </div>
                    </div>
                    <div class="toolSectionPad"/>
                    <div class="toolSectionPad"/>
                    <div class="toolSectionTitle" id="title_XXinternalXXworkflow">
                        <span>
                            ${_l("Workflows")}
                        </span>
                    </div>
                        <div id="internal-workflows" class="toolSectionBody">
                            <div class="toolSectionBg"/>
                        </div>
                </div>`;
    },

    toString: function() {
        return "toolPanel";
    }
});

export default ToolPanel;
