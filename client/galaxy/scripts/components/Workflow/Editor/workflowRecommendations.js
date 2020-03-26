import _ from "underscore";
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

function getWorkflowPath(wf_steps, current_node_id, current_node_name) {
        let steps = {};
        let step_names = {};
        for (let stp_idx in wf_steps.steps) {
            let step = wf_steps.steps[stp_idx];
            let input_connections = step.input_connections;
            step_names[step.id] = getToolId(step.content_id);
            for (let ic_idx in input_connections) {
                let ic = input_connections[ic_idx];
                if(ic !== null && ic !== undefined) {
                    let prev_conn = [];
                    for (let conn of ic) {
                        prev_conn.push(conn.id.toString());
                    }
                    steps[step.id.toString()] = prev_conn;
                }
            }
        }
        // recursive call to determine path
        function readPaths(node_id, ph) {
            for (let st in steps) {
                if (parseInt(st) === parseInt(node_id)) {
                    let parent_id = parseInt(steps[st][0]);
                    if (parent_id !== undefined && parent_id !== null) {
                        ph.push(parent_id);
                        if (steps[parent_id] !== undefined && steps[parent_id] !== null) {
                            readPaths(parent_id, ph);
                        }
                    }
                }
            }
            return ph;
        }
        let ph = [];
        let step_names_list = [];
        ph.push(current_node_id);
        ph = readPaths(current_node_id, ph);
        for (let s_idx of ph) {
            let s_name = step_names[s_idx.toString()];
            if (s_name !== undefined && s_name !== null) {
                step_names_list.push(s_name);
            }
        }
        return step_names_list.join(",");
}

export function getToolRecommendations(props) {
        const workflowSimple = props.node.app.to_simple();
        const node = props.node;
        const toolId = getToolId(node.content_id);
        const toolSequence = getWorkflowPath(workflowSimple, node.id, toolId);
        
        // show tool recommendations
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
