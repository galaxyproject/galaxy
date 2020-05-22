import $ from "jquery";
import { mountWorkflowNode } from "components/Workflow/Editor/mount";
import Connector from "./connector";
import WorkflowCanvas from "./canvas";
import EventEmitter from "events";
import Vue from "vue";

class Workflow extends EventEmitter {
    constructor(options, canvas_container) {
        super();
        this.ext_to_type = options.datatypes_mapping.ext_to_class_name;
        this.type_to_type = options.datatypes_mapping.class_to_classes;
        this.canvas_container = $(canvas_container);
        this.nodes = {};
        this.name = null;
        this.has_changes = false;
        this.workflow_version = 0;
        this.nodeId = 0;

        // Canvas overview management
        this.canvas_manager = new WorkflowCanvas(this, $("#canvas-viewport"), $("#overview-container"));

        // On load, set the size to the pref stored in local storage if it exists
        const overview_size = localStorage.getItem("overview-size");
        if (overview_size !== undefined) {
            $(".workflow-overview").css({
                width: overview_size,
                height: overview_size,
            });
        }

        // Stores the size of the overview into local storage when it's resized
        $(".workflow-overview").bind("dragend", function (e, d) {
            const op = $(this).offsetParent();
            const opo = op.offset();
            const new_size = Math.max(op.width() - (d.offsetX - opo.left), op.height() - (d.offsetY - opo.top));
            localStorage.setItem("overview-size", `${new_size}px`);
        });

        // Unload handler
        window.onbeforeunload = () => {
            if (this.has_changes) {
                return "There are unsaved changes to your workflow which will be lost.";
            }
        };
    }
    setNode(node, data) {
        data.workflow_outputs = data.outputs.map((o) => {
            return {
                output_name: o.name,
                label: o.label,
            };
        });
        node.initData(data);
        Vue.nextTick(() => {
            node.updateData(data);
            this._activateNode(node);
        });
    }
    isSubType(child, parent) {
        child = this.ext_to_type[child];
        parent = this.ext_to_type[parent];
        return this.type_to_type[child] && parent in this.type_to_type[child];
    }
    createNode(type, name, content_id) {
        const node = this.buildNode(type, name, content_id);
        this.canvas_manager.draw_overview();
        this._activateNode(node);
        return node;
    }
    buildNode(type, name, content_id) {
        const self = this;

        // Create node wrapper
        const container = document.createElement("div");
        document.getElementById("canvas-container").appendChild(container);

        // Mount node component as child dom to node wrapper
        const node = mountWorkflowNode(container, {
            type: type,
            name: name,
            node: node,
            id: this.nodeId,
            contentId: content_id,
            getManager: () => {
                return this;
            },
        });

        // Increase node id counter
        this.nodeId++;

        // Set initial scroll position
        const $f = $(node.$el);
        $f.css("left", $(window).scrollLeft() + 20);
        $f.css("top", $(window).scrollTop() + 20);

        // Position in container
        const o = $("#canvas-container").position();
        const p = $("#canvas-container").parent();
        const width = $f.outerWidth() + 50;
        const height = $f.height();
        $f.css({
            left: -o.left + p.width() / 2 - width / 2,
            top: -o.top + p.height() / 2 - height / 2,
        });
        $f.css("width", width);
        $f.bind("dragstart", () => {
            self._activateNode(node);
        })
            .bind("dragend", function () {
                self.nodeChanged(node);
                self.canvas_manager.draw_overview();
            })
            .bind("dragclickonly", () => {
                self._activateNode(node);
            })
            .bind("drag", function (e, d) {
                // Move
                const po = $(this).offsetParent().offset();
                // Find relative offset and scale by zoom
                const x = (d.offsetX - po.left) / self.canvas_manager.canvasZoom;
                const y = (d.offsetY - po.top) / self.canvas_manager.canvasZoom;
                $(this).css({ left: x, top: y });
                // Redraw
                $(this)
                    .find(".terminal")
                    .each(function () {
                        this.terminal.redraw();
                    });
            });

        // Set node attributes and add to nodes list
        this.nodes[node.id] = node;
        this.has_changes = true;
        node.workflow = this;
        return node;
    }
    removeNode(node) {
        if (this.activeNode == node) {
            this._clearActiveNode();
        }
        delete this.nodes[node.id];
        this.has_changes = true;
        this.canvas_manager.draw_overview();
        this.emit("onRemoveNode");
    }
    fromSimple(data, appendData) {
        const self = this;
        let offset = 0;
        if (!appendData) {
            this.name = data.name;
            this._removeAll();
        } else {
            offset = this.nodeId;
        }
        // First pass, nodes
        let using_workflow_outputs = false;
        this.workflow_version = data.version;
        this.report = data.report || {};
        Object.values(data.steps).forEach((step) => {
            const node = self.buildNode(step.type, step.name, step.content_id);
            // If workflow being copied into another, wipe UUID and let
            // Galaxy assign new ones.
            if (appendData) {
                step.uuid = null;
                step.workflow_outputs.forEach((workflow_output) => {
                    workflow_output.uuid = null;
                });
            }
            node.initData(step);
            Vue.nextTick(() => {
                if (step.position) {
                    node.element.style.top = step.position.top + "px";
                    node.element.style.left = step.position.left + "px";
                }
                self.nodes[node.id] = node;

                // For older workflows, it's possible to have HideDataset PJAs, but not WorkflowOutputs.
                // Check for either, and then add outputs in the next pass.
                if (!using_workflow_outputs) {
                    if (node.activeOutputs.count() > 0) {
                        using_workflow_outputs = true;
                    } else {
                        Object.values(node.postJobActions).forEach((pja) => {
                            if (pja.action_type === "HideDatasetAction") {
                                using_workflow_outputs = true;
                            }
                        });
                    }
                }
            });
        });
        Vue.nextTick(() => {
            // Second pass, connections
            Object.entries(data.steps).forEach(([id, step]) => {
                const nodeIndex = parseInt(id) + offset;
                const node = self.nodes[nodeIndex];
                Object.entries(step.input_connections).forEach(([k, v]) => {
                    if (v) {
                        if (!Array.isArray(v)) {
                            v = [v];
                        }
                        v.forEach((x) => {
                            const otherNodeIndex = parseInt(x.id) + offset;
                            const otherNode = self.nodes[otherNodeIndex];
                            const c = new Connector(this.canvas_manager);
                            c.connect(otherNode.outputTerminals[x.output_name], node.inputTerminals[k]);
                            c.redraw();
                        });
                    }
                });
                if (using_workflow_outputs) {
                    // Ensure that every output terminal has a WorkflowOutput or HideDatasetAction.
                    Object.values(node.outputs).forEach((ot) => {
                        if (node.postJobActions[`HideDatasetAction${ot.name}`] === undefined) {
                            node.activeOutputs.add(ot.name);
                            self.has_changes = true;
                        }
                    });
                }
                self.has_changes = false;
            });
            self.canvas_manager.draw_overview(true);
        });
    }
    toSimple() {
        const nodes = {};
        this._rectifyOutputs();
        Object.values(this.nodes).forEach((node) => {
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
                position: node.element.getBoundingClientRect(),
                annotation: node.annotation,
                post_job_actions: node.postJobActions,
                uuid: node.uuid,
                label: node.label,
                workflow_outputs: node.activeOutputs.getAll(),
            };
            nodes[node.id] = node_data;
        });
        const report = this.report;
        return { steps: nodes, report: report };
    }
    _removeAll() {
        Object.values(this.nodes).forEach((node) => {
            node.onDestroy();
            this.removeNode(node);
        });
    }
    _rectifyOutputs() {
        // Find out if we're using workflow_outputs or not.
        let using_workflow_outputs = false;
        let has_existing_pjas = false;
        Object.values(this.nodes).forEach((node) => {
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
            Object.values(this.nodes).forEach((node) => {
                let nodeChanged = false;
                if (node.postJobActions === null) {
                    node.postJobActions = {};
                    nodeChanged = true;
                }
                const pjas_to_rem = [];
                Object.entries(node.postJobActions).forEach(([pja_id, pja]) => {
                    if (pja.action_type == "HideDatasetAction") {
                        pjas_to_rem.push(pja_id);
                    }
                });
                if (pjas_to_rem.length > 0) {
                    pjas_to_rem.forEach((pja_name) => {
                        nodeChanged = true;
                        delete node.postJobActions[pja_name];
                    });
                }
                if (using_workflow_outputs) {
                    Object.values(node.outputs).forEach((ot) => {
                        const create_pja = !node.activeOutputs.exists(ot.name);
                        if (create_pja === true) {
                            nodeChanged = true;
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
                // lastly, if this is the active node, and we made changes, reload the display at right.
                if (this.activeNode == node && nodeChanged === true) {
                    this._reloadActiveNode();
                }
            });
        }
    }
    _reloadActiveNode() {
        if (this.activeNode) {
            const node = this.activeNode;
            this._clearActiveNode();
            this._activateNode(node);
        }
    }
    _clearActiveNode() {
        if (this.activeNode) {
            this.activeNode.makeInactive();
            this.activeNode = null;
        }
        document.activeElement.blur();
        this.emit("onClearActiveNode");
    }
    _activateNode(node) {
        if (this.activeNode != node) {
            this._clearActiveNode();
            node.makeActive();
            this.activeNode = node;
        }
        this.emit("onActiveNode", node);
    }
    nodeChanged() {
        this.has_changes = true;
    }
    layoutAuto() {
        this.layout();
        this.canvas_manager.draw_overview(true);
    }
    layout() {
        this.has_changes = true;
        // Prepare predecessor / successor tracking
        const n_pred = {};
        const successors = {};
        // First pass to initialize arrays even for nodes with no connections
        Object.keys(this.nodes).forEach((id) => {
            if (n_pred[id] === undefined) {
                n_pred[id] = 0;
            }
            if (successors[id] === undefined) {
                successors[id] = [];
            }
        });
        // Second pass to count predecessors and successors
        Object.values(this.nodes).forEach((node) => {
            Object.values(node.inputTerminals).forEach((t) => {
                t.connectors.forEach((c) => {
                    // A connection exists from `other` to `node`
                    const other = c.outputHandle.node;
                    // node gains a predecessor
                    n_pred[node.id] += 1;
                    // other gains a successor
                    successors[other.id].push(node.id);
                });
            });
        });
        // Assemble order, tracking levels
        const node_ids_by_level = [];
        for (;;) {
            // Everything without a predecessor
            const level_parents = [];
            for (const pred_k in n_pred) {
                if (n_pred[pred_k] === 0) {
                    level_parents.push(pred_k);
                }
            }
            if (level_parents.length === 0) {
                break;
            }
            node_ids_by_level.push(level_parents);
            // Remove the parents from this level, and decrement the number
            // of predecessors for each successor
            for (const k in level_parents) {
                const v = level_parents[k];
                delete n_pred[v];
                for (const sk in successors[v]) {
                    n_pred[successors[v][sk]] -= 1;
                }
            }
        }
        if (n_pred.length) {
            // ERROR: CYCLE! Currently we do nothing
            return;
        }
        // Layout each level
        const all_nodes = this.nodes;
        const h_pad = 80;
        const v_pad = 30;
        let left = h_pad;
        node_ids_by_level.forEach((ids) => {
            // We keep nodes in the same order in a level to give the user
            // some control over ordering
            ids.sort(
                (a, b) =>
                    all_nodes[a].element.getBoundingClientRect().top - all_nodes[b].element.getBoundingClientRect().top
            );
            // Position each node
            let max_width = 0;
            let top = v_pad;
            ids.forEach((id) => {
                const node = all_nodes[id];
                const element = $(node.element);
                $(element).css({ top: top, left: left });
                max_width = Math.max(max_width, $(element).width());
                top += $(element).height() + v_pad;
            });
            left += max_width + h_pad;
        });
        // Need to redraw all connectors
        Object.values(all_nodes).forEach((node) => {
            node.onRedraw();
        });
    }
}

export default Workflow;
