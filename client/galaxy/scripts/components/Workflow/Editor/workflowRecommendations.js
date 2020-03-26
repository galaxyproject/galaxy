import $ from "jquery";
import Vue from "vue";
import WorkflowToolRecommendations from "components/Workflow/Editor/WorkflowRecommendationsVue";

function getToolId(toolId) {
    if (toolId !== undefined && toolId !== null && toolId.indexOf("/") > -1) {
        let toolIdSlash = toolId.split("/");
        toolId = toolIdSlash[toolIdSlash.length - 2];
    }
    return toolId;
}

function getWorkflowPath(wfSteps, currentNodeId) {
        let steps = {};
        let stepNames = {};
        for (const stpIdx in wfSteps.steps) {
            const step = wfSteps.steps[stpIdx];
            const inputConnections = step.inputConnections;
            stepNames[step.id] = getToolId(step.content_id);
            for (const icIdx in inputConnections) {
                const ic = inputConnections[icIdx];
                if(ic !== null && ic !== undefined) {
                    let prevConn = [];
                    for (const conn of ic) {
                        prevConn.push(conn.id.toString());
                    }
                    steps[step.id.toString()] = prevConn;
                }
            }
        }
        // recursive call to determine path
        function readPaths(nodeId, ph) {
            for (const st in steps) {
                if (parseInt(st) === parseInt(nodeId)) {
                    const parentId = parseInt(steps[st][0]);
                    if (parentId !== undefined && parentId !== null) {
                        ph.push(parentId);
                        if (steps[parentId] !== undefined && steps[parentId] !== null) {
                            readPaths(parentId, ph);
                        }
                    }
                }
            }
            return ph;
        }
        let ph = [];
        let stepNamesList = [];
        ph.push(currentNodeId);
        ph = readPaths(currentNodeId, ph);
        for (const sIdx of ph) {
            const sName = stepNames[sIdx.toString()];
            if (sName !== undefined && sName !== null) {
                stepNamesList.push(sName);
            }
        }
        return stepNamesList.join(",");
}

export function getToolRecommendations(props) {
        const workflowSimple = props.node.app.to_simple();
        const node = props.node;
        const toolId = getToolId(node.content_id);
        const toolSequence = getWorkflowPath(workflowSimple, node.id);
        const ToolRecommendationInstance = Vue.extend(WorkflowToolRecommendations);
        const vm = document.createElement("div");
        $("body").append(vm);
        const instance = new ToolRecommendationInstance({
             propsData: {
                 workflowManager: props,
                 toolSequence: toolSequence
             },
        });
        instance.$mount(vm);
    }
