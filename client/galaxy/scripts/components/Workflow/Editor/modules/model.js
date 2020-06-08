import Connector from "./connector";
import Vue from "vue";

export function fromSimple(workflow, data, appendData = false) {
    let offset = 0;
    if (appendData) {
        offset = workflow.nodeIndex;
    } else {
        workflow.name = data.name;
        workflow.steps.splice();
    }
    workflow.workflow_version = data.version;
    workflow.report = data.report || {};
    workflow.has_changes = false;
    Object.values(data.steps).forEach((step) => {
        workflow.steps.push({
            ...step
        });
    });
    // If workflow being copied into another, wipe UUID and let
    // Galaxy assign new ones.
    if (appendData) {
        Object.values(data.steps).forEach((step) => {
            step.uuid = null;
            step.workflow_outputs.forEach((workflow_output) => {
                workflow_output.uuid = null;
            });
        });
    }
    Vue.nextTick(() => {
        // Second pass, connections
        Object.entries(data.steps).forEach(([id, step]) => {
            const nodeIndex = parseInt(id) + offset;
            const node = workflow.nodes[nodeIndex];
            Object.entries(step.input_connections).forEach(([k, v]) => {
                if (v) {
                    if (!Array.isArray(v)) {
                        v = [v];
                    }
                    v.forEach((x) => {
                        const otherNodeIndex = parseInt(x.id) + offset;
                        const otherNode = workflow.nodes[otherNodeIndex];
                        const c = new Connector(workflow.manager.canvas_manager);
                        c.connect(otherNode.outputTerminals[x.output_name], node.inputTerminals[k]);
                        c.redraw();
                    });
                }
            });

            // Older workflows contain HideDatasetActions only, but no active outputs yet.
            Object.values(node.outputs).forEach((ot) => {
                if (!node.postJobActions[`HideDatasetAction${ot.name}`]) {
                    node.activeOutputs.add(ot.name);
                }
            });
        });
    });
}
