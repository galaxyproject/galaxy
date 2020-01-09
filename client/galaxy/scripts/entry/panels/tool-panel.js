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
    initialize: function() {
        const Galaxy = getGalaxyInstance();
        const appRoot = getAppRoot();

        // add uploader button to Galaxy object
        Galaxy.upload = new Upload({
            upload_path: Galaxy.config.nginx_upload_path || `${appRoot}api/tools`,
            chunk_upload_size: Galaxy.config.chunk_upload_size,
            ftp_upload_site: Galaxy.config.ftp_upload_site,
            default_genome: Galaxy.config.default_genome,
            default_extension: Galaxy.config.default_extension
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

    getPropsData: function() {
        const Galaxy = getGalaxyInstance();
        const appRoot = getAppRoot();

        /** @type {Object[]} descriptions of user's workflows to be shown in the tool menu */
        const storedWorkflowMenuEntries = Galaxy.config.stored_workflow_menu_entries || [];

        // create tool search, tool panel, and tool panel view.
        const tool_search = new Tools.ToolSearch({
            hidden: false
        });
        const tools = new Tools.ToolCollection(Galaxy.config.toolbox);
        const toolPanel = new Tools.ToolPanel({
            tool_search: tool_search,
            tools: tools,
            layout: Galaxy.config.toolbox_in_panel
        });

        return {
            side: "left",
            currentPanel: ToolBox,
            currentPanelProperties: {
                appRoot: getAppRoot(),
                toolsTitle: _l("Tools"),
                toolsLayout: getToolsLayout(toolPanel),
                isUser: !!(Galaxy.user && Galaxy.user.id),
                workflowsTitle: _l("Workflows"),
                workflows: [
                    {
                        title: _l("All workflows"),
                        href: `${appRoot}workflows/list`,
                        id: "list"
                    },
                    ...storedWorkflowMenuEntries.map(menuEntry => {
                        return {
                            title: menuEntry["stored_workflow"]["name"],
                            href: `${appRoot}workflows/run?id=${menuEntry["encoded_stored_workflow_id"]}`,
                            id: menuEntry["encoded_stored_workflow_id"]
                        };
                    })
                ]
            }
        };
    },

    toString: function() {
        return "toolPanel";
    }
});

export default ToolPanel;
