import $ from "jquery";
import WorkflowCanvas from "./canvas";
import EventEmitter from "events";
import Vue from "vue";

class Workflow extends EventEmitter {
    constructor(options, canvas_container) {
        super();
        this.ext_to_type = options.datatypes_mapping.ext_to_class_name;
        this.type_to_type = options.datatypes_mapping.class_to_classes;
        this.canvas_container = $(canvas_container);
        this.nodes = options.nodes;
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
            this.canvas_manager.draw_overview();
            this._activateNode(node);
        });
    }
    isSubType(child, parent) {
        child = this.ext_to_type[child];
        parent = this.ext_to_type[parent];
        return this.type_to_type[child] && parent in this.type_to_type[child];
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
