import Connector from "./connector";
import Vue from "vue";

export async function fromSimple(workflow, data, appendData = false) {
    let offset = 0;
    if (appendData) {
        offset = workflow.nodeIndex;
    } else {
        workflow.nodeIndex = 0;
        workflow.name = data.name;
        workflow.annotation = data.annotation;
        workflow.license = data.license;
        workflow.creator = data.creator;
        Object.values(workflow.nodes).forEach((node) => {
            node.onRemove();
        });
    }
    await Vue.nextTick();
    workflow.version = data.version;
    workflow.report = data.report || {};
    Object.values(data.steps).forEach((step) => {
        // If workflow being copied into another, wipe UUID and let
        // Galaxy assign new ones.
        if (appendData) {
            step.uuid = null;
        }
        Vue.set(workflow.steps, workflow.nodeIndex++, {
            ...step,
        });
    });
    await Vue.nextTick();
    // Second pass, connections
    let using_workflow_outputs = false;
    Object.entries(data.steps).forEach(([id, step]) => {
        if (step.workflow_outputs && step.workflow_outputs.length > 0) {
            using_workflow_outputs = true;
        }
    });

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
                    const c = new Connector(workflow.canvasManager);
                    c.connect(otherNode.outputTerminals[x.output_name], node.inputTerminals[k]);
                    c.redraw();
                });
            }
        });

        if (!using_workflow_outputs) {
            // Older workflows contain HideDatasetActions only, but no active outputs yet.
            Object.values(node.outputs).forEach((ot) => {
                if (!node.postJobActions[`HideDatasetAction${ot.name}`]) {
                    node.activeOutputs.add(ot.name);
                }
            });
        }
    });
}

export function toSimple(workflow) {
    const nodes = {};
    const canvasZoom = workflow.canvasManager.canvasZoom;
    _rectifyOutputs(workflow);
    Object.values(workflow.nodes).forEach((node) => {
        const input_connections = {};
        Object.values(node.inputTerminals).forEach((t) => {
            input_connections[t.name] = null;
            // There should only be 0 or 1 connectors, so this is
            // really a sneaky if statement
            const cons = [];
            t.connectors.forEach((c, i) => {
                if (c.outputHandle) {
                    const con_dict = {
                        id: c.outputHandle.node.id,
                        output_name: c.outputHandle.name,
                    };
                    const input_subworkflow_step_id = t.attributes.input.input_subworkflow_step_id;
                    if (input_subworkflow_step_id !== undefined) {
                        con_dict.input_subworkflow_step_id = input_subworkflow_step_id;
                    }
                    cons[i] = con_dict;
                    input_connections[t.name] = cons;
                }
            });
        });
        const postJobActions = {};
        if (node.postJobActions) {
            Object.values(node.postJobActions).forEach((act) => {
                const pja = {
                    action_type: act.action_type,
                    output_name: act.output_name,
                    action_arguments: act.action_arguments,
                };
                postJobActions[act.action_type + act.output_name] = null;
                postJobActions[act.action_type + act.output_name] = pja;
            });
        }
        const node_data = {
            id: node.id,
            type: node.type,
            content_id: node.content_id,
            tool_version: node.config_form ? node.config_form.version : null,
            tool_state: node.tool_state,
            errors: node.errors,
            input_connections: input_connections,
            position: _scaledNodePosition(node.element, canvasZoom),
            annotation: node.annotation,
            post_job_actions: node.postJobActions,
            uuid: node.uuid,
            label: node.label,
            workflow_outputs: node.activeOutputs.getAll(),
        };
        nodes[node.id] = node_data;
    });
    const report = workflow.report;
    const license = workflow.license;
    const creator = workflow.creator;
    const annotation = workflow.annotation;
    const name = workflow.name;
    return { steps: nodes, report, license, creator, annotation, name };
}

function _scaledNodePosition(element, canvasZoom) {
    const rect = element.getBoundingClientRect();
    const coords = {
        left: rect.left / canvasZoom,
        top: rect.top / canvasZoom,
    };
    return coords;
}

function _rectifyOutputs(workflow) {
    // Find out if we're using workflow_outputs or not.
    let using_workflow_outputs = false;
    let has_existing_pjas = false;
    Object.values(workflow.nodes).forEach((node) => {
        if (node.activeOutputs.count() > 0) {
            using_workflow_outputs = true;
        }
        Object.values(node.postJobActions).forEach((pja) => {
            if (pja.action_type === "HideDatasetAction") {
                has_existing_pjas = true;
            }
        });
    });
    if (using_workflow_outputs !== false || has_existing_pjas !== false) {
        // Using workflow outputs, or has existing pjas.  Remove all PJAs and recreate based on outputs.
        Object.values(workflow.nodes).forEach((node) => {
            if (node.postJobActions === null) {
                node.postJobActions = {};
            }
            const pjas_to_rem = [];
            Object.entries(node.postJobActions).forEach(([pja_id, pja]) => {
                if (pja.action_type == "HideDatasetAction") {
                    pjas_to_rem.push(pja_id);
                }
            });
            if (pjas_to_rem.length > 0) {
                pjas_to_rem.forEach((pja_name) => {
                    delete node.postJobActions[pja_name];
                });
            }
            if (using_workflow_outputs) {
                Object.values(node.outputs).forEach((ot) => {
                    const create_pja = !node.activeOutputs.exists(ot.name);
                    if (create_pja === true) {
                        const pja = {
                            action_type: "HideDatasetAction",
                            output_name: ot.name,
                            action_arguments: {},
                        };
                        node.postJobActions[`HideDatasetAction${ot.name}`] = null;
                        node.postJobActions[`HideDatasetAction${ot.name}`] = pja;
                    }
                });
            }
        });
    }
}
