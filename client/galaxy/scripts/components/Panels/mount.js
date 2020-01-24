/**
 * Endpoint for mounting Panel components
 */
import Vue from "vue";
import _l from "utils/localization";
import SidePanel from "./SidePanel";
import ToolBoxWorkflow from "./ToolBoxWorkflow";

export const mountToolBoxWorkflow = options => {
    const component = Vue.extend(SidePanel);
    return new component({
        propsData: {
            side: "left",
            currentPanel: ToolBoxWorkflow,
            currentPanelProperties: {
                toolbox: options.toolbox,
                workflowGlobals: options.workflow_globals,
                moduleSections: options.module_sections,
                dataManagers: {
                    name: _l("Data Managers"),
                    elems: options.data_managers
                },
                workflowSection: {
                    name: _l("Workflows"),
                    elems: options.workflows
                }
            }
        },
        el: "#left"
    });
};
