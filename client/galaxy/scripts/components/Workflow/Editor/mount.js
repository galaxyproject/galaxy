/**
 * Endpoint for mounting WorkflowEditor from non-Vue environment (editor.mako).
 */
import Vue from "vue";
import SidePanel from "components/Panels/SidePanel";
import WorkflowEditor from "./WorkflowEditor";
import WorkflowPanel from "./WorkflowPanel";

export const mountWorkflowEditor = editorConfig => {
    const propsData = { editorConfig };
    const component = Vue.extend(WorkflowEditor);
    return new component({ propsData: propsData, el: "#center" });
};

export const mountWorkflowPanel = propsData => {
    const component = Vue.extend(SidePanel);
    return new component({
        propsData: {
            side: "right",
            currentPanel: WorkflowPanel,
            currentPanelProperties: propsData
        },
        el: "#right"
    });
};