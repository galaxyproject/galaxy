/**
 * Endpoint for mounting WorkflowEditor from non-Vue environment (editor.mako).
 */
import Vue from "vue";
import SidePanel from "components/Panels/SidePanel";
import Index from "./Index";
import Node from "./Node";
import WorkflowPanel from "./WorkflowPanel";
import ToolBoxWorkflow from "components/Panels/ToolBoxWorkflow";
import _l from "utils/localization";

export const mountWorkflowEditor = editorConfig => {
    const rightPanel = Vue.extend(SidePanel);
    new rightPanel({
        propsData: {
            side: "right",
            currentPanel: WorkflowPanel,
            currentPanelProperties: {
                id: editorConfig.id,
                name: editorConfig.name,
                tags: editorConfig.tags,
                annotation: editorConfig.annotation
            }
        },
        el: "#right"
    });
    const leftPanel = Vue.extend(SidePanel);
    new leftPanel({
        propsData: {
            side: "left",
            currentPanel: ToolBoxWorkflow,
            currentPanelProperties: {
                toolbox: editorConfig.toolbox,
                workflowGlobals: editorConfig.workflow_globals,
                moduleSections: editorConfig.module_sections,
                dataManagers: {
                    name: _l("Data Managers"),
                    elems: editorConfig.data_managers
                },
                workflowSection: {
                    name: _l("Workflows"),
                    elems: editorConfig.workflows
                }
            }
        },
        el: "#left"
    });
    const component = Vue.extend(Index);
    return new component({ propsData: {
        editorConfig
    }, el: "#center" });
};

export const mountWorkflowNode = (container, propsData) => {
    const component = Vue.extend(Node);
    return new component({ propsData: propsData, el: container });
};
