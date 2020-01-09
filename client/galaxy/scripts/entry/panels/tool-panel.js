import Backbone from "backbone";
import Tools from "mvc/tool/tools";
import Upload from "mvc/upload/upload-view";
import _l from "utils/localization";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import Vue from "vue";
import ToolBox from "../../components/Panels/ToolBox.vue";
import SidePanel from "../../components/Panels/SidePanel.vue";
import { getToolsLayout } from "../../components/Panels/utilities.js";
import { mountVueComponent } from "../../utils/mountVueComponent";

const ToolPanel = Backbone.View.extend({
    initialize: function(page, options) {
        const Galaxy = getGalaxyInstance();
        const appRoot = getAppRoot();

        // access configuration options
        const config = options.config;
        this.root = options.root;

        /** @type {Object[]} descriptions of user's workflows to be shown in the tool menu */
        this.stored_workflow_menu_entries = config.stored_workflow_menu_entries || [];

        // create tool search, tool panel, and tool panel view.
        const tool_search = new Tools.ToolSearch({
            hidden: false
        });
        const tools = new Tools.ToolCollection(config.toolbox);
        this.tool_panel = new Tools.ToolPanel({
            tool_search: tool_search,
            tools: tools,
            layout: config.toolbox_in_panel
        });

        // add uploader button to Galaxy object
        Galaxy.upload = new Upload({
            upload_path: config.nginx_upload_path || `${appRoot}api/tools`,
            chunk_upload_size: config.chunk_upload_size,
            ftp_upload_site: config.ftp_upload_site,
            default_genome: config.default_genome,
            default_extension: config.default_extension
        });

        // components for panel definition
        this.model = new Backbone.Model({
            title: _l("Tools")
        });
    },

    isVueWrapper: true,

    mountVueComponent: function(el) {
        return mountVueComponent(SidePanel)(this.getPropsData(), el);
    },

    getVueComponent: function() {
        const SidePanelClass = Vue.extend(SidePanel);
        return new SidePanelClass({
            propsData: this.getPropsData()
        });
    },

    onOpen: function(e, tool) {
        const Galaxy = getGalaxyInstance();
        if (tool.id === "upload1") {
            e.preventDefault();
            Galaxy.upload.show();
        } else if (tool.form_style === "regular") {
            e.preventDefault();
            Galaxy.router.push("/", {
                tool_id: tool.id,
                version: tool.version
            });
        }
    },

    getPropsData: function() {
        return {
            side: "left",
            currentPanel: ToolBox,
            currentPanelProperties: this.getProperties(),
            currentPanelOnOpen: this.onOpen
        };
    },

    getProperties: function() {
        const Galaxy = getGalaxyInstance();
        const appRoot = getAppRoot();
        return {
            appRoot: getAppRoot(),
            toolsTitle: _l("Tools"),
            toolsLayout: getToolsLayout(this.tool_panel),
            isUser: !!(Galaxy.user && Galaxy.user.id),
            workflowsTitle: _l("Workflows"),
            workflows: [
                {
                    title: _l("All workflows"),
                    href: `${appRoot}workflows/list`,
                    id: "list"
                },
                ...this.stored_workflow_menu_entries.map(menuEntry => {
                    return {
                        title: menuEntry["stored_workflow"]["name"],
                        href: `${appRoot}workflows/run?id=${menuEntry["encoded_stored_workflow_id"]}`,
                        id: menuEntry["encoded_stored_workflow_id"]
                    };
                })
            ]
        };
    },

    toString: function() {
        return "toolPanel";
    }
});

export default ToolPanel;
