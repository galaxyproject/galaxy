/**
 * Endpoint for mounting WorkflowEditor from non-Vue environment (editor.mako).
 */
import Vue from "vue";
import SidePanel from "components/Panels/SidePanel";
import Index from "./Index";
import Node from "./Node";
import WorkflowPanel from "./WorkflowPanel";

export const mountWorkflowEditor = editorConfig => {
    const propsData = { editorConfig };
    const component = Vue.extend(Index);
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

export const mountWorkflowNode = (parent, propsData) => {
    const component = Vue.extend(Node);
    const container = document.createElement("div");
    parent.appendChild(container);
    return new component({ propsData: propsData, el: container });
};