import $ from "jquery";
import Connector from "mvc/workflow/workflow-connector";
import { Toast } from "ui/toast";
import { Node } from "mvc/workflow/workflow-node";
import { mountWorkflowNode } from "components/Workflow/Editor/mount";
import WorkflowCanvas from "mvc/workflow/workflow-canvas";
import EventEmitter from "events";

class Workflow extends EventEmitter {
    constructor(options, canvas_container) {
        super();
        this.ext_to_type = options.datatypes_mapping.ext_to_class_name;
        this.type_to_type = options.datatypes_mapping.class_to_classes;
        this.canvas_container = $(canvas_container);
        this.id_counter = 0;
        this.nodes = {};
        this.name = null;
        this.has_changes = false;
        this.workflowOutputLabels = {};
        this.workflow_version = 0;

        // Canvas overview management
        this.canvas_manager = new WorkflowCanvas(this, $("#canvas-viewport"), $("#overview-container"));

        // On load, set the size to the pref stored in local storage if it exists
        var overview_size = localStorage.getItem("overview-size");
        if (overview_size !== undefined) {
            $(".workflow-overview").css({
                width: overview_size,
                height: overview_size,
            });
        }

        // Stores the size of the overview into local storage when it's resized
        $(".workflow-overview").bind("dragend", function (e, d) {
            var op = $(this).offsetParent();
            var opo = op.offset();
            var new_size = Math.max(op.width() - (d.offsetX - opo.left), op.height() - (d.offsetY - opo.top));
            localStorage.setItem("overview-size", `${new_size}px`);
        });

        // Unload handler
        window.onbeforeunload = () => {
            if (this.has_changes) {
                return "There are unsaved changes to your workflow which will be lost.";
            }
        };
    }
    set_node(node, data) {
        node.init_field_data(data);
        node.update_field_data(data);
        Object.values(node.output_terminals).forEach((ot) => {
            node.addWorkflowOutput(ot.name);
            node.markWorkflowOutput(ot.name);
        });
        this.activate_node(node);
    }
    isSubType(child, parent) {
        child = this.ext_to_type[child];
        parent = this.ext_to_type[parent];
        return this.type_to_type[child] && parent in this.type_to_type[child];
    }
    canLabelOutputWith(label) {
        if (label) {
            return !(label in this.workflowOutputLabels);
        } else {
            // empty labels are non-exclusive, so allow this one.
            return true;
        }
    }
    registerOutputLabel(label) {
        if (label) {
            this.workflowOutputLabels[label] = true;
        }
    }
    unregisterOutputLabel(label) {
        if (label) {
            delete this.workflowOutputLabels[label];
        }
    }
    updateOutputLabel(fromLabel, toLabel) {
        if (fromLabel) {
            this.unregisterOutputLabel(fromLabel);
        }
        if (!this.canLabelOutputWith(toLabel)) {
            Toast.warning(
                `Workflow contains duplicate workflow output labels ${toLabel}. This must be fixed before it can be saved.`
            );
        }
        if (toLabel) {
            this.registerOutputLabel(toLabel);
        }
    }
    attemptUpdateOutputLabel(node, outputName, label) {
        if (this.canLabelOutputWith(label)) {
            node.labelWorkflowOutput(outputName, label);
            return true;
        } else {
            return false;
        }
    }
    updateDatatype(node, outputName, newDatatype) {
        node.changeOutputDatatype(outputName, newDatatype);
        return true;
    }
    create_node(type, title_text, content_id) {
        var node = this.prebuildNode(type, title_text, content_id);
        this.add_node(node);
        this.fit_canvas_to_nodes();
        this.canvas_manager.draw_overview();
        this.activate_node(node);
        return node;
    }
    add_node(node) {
        node.id = this.id_counter;
        node.element.attr("id", `wf-node-step-${node.id}`);
        node.element.attr("node-label", node.label);
        this.id_counter++;
        this.nodes[node.id] = node;
        this.has_changes = true;
        node.workflow = this;
    }
    prebuildNode(type, title_text, content_id) {
        var self = this;

        // Create node wrapper
        const container = document.createElement("div");
        container.className = "workflow-node";
        document.getElementById("canvas-container").appendChild(container);
        var $f = $(container);

        // Create backbone model and view
        var node = new Node(this, { element: $f });
        node.type = type;
        node.content_id = content_id;

        // Mount node component as child dom to node wrapper
        const child = document.createElement("div");
        container.appendChild(child);
        mountWorkflowNode(child, {
            id: content_id,
            type: type,
            title: title_text,
            node: node,
        });

        // Set initial scroll position
        $f.css("left", $(window).scrollLeft() + 20);
        $f.css("top", $(window).scrollTop() + 20);

        // Position in container
        var o = $("#canvas-container").position();
        var p = $("#canvas-container").parent();
        var width = $f.outerWidth() + 50;
        var height = $f.height();
        $f.css({
            left: -o.left + p.width() / 2 - width / 2,
            top: -o.top + p.height() / 2 - height / 2,
        });
        $f.css("width", width);
        $f.bind("dragstart", () => {
            self.activate_node(node);
        })
            .bind("dragend", function () {
                self.node_changed(node);
                self.fit_canvas_to_nodes();
                self.canvas_manager.draw_overview();
            })
            .bind("dragclickonly", () => {
                self.activate_node(node);
            })
            .bind("drag", function (e, d) {
                // Move
                var po = $(this).offsetParent().offset();
                // Find relative offset and scale by zoom
                var x = (d.offsetX - po.left) / self.canvas_manager.canvasZoom;
                var y = (d.offsetY - po.top) / self.canvas_manager.canvasZoom;
                $(this).css({ left: x, top: y });
                // Redraw
                $(this)
                    .find(".terminal")
                    .each(function () {
                        this.terminal.redraw();
                    });
            });
        return node;
    }
    remove_node(node) {
        if (this.active_node == node) {
            this.clear_active_node();
        }
        delete this.nodes[node.id];
        this.has_changes = true;
        this.emit("onRemoveNode");
    }
    remove_all() {
        var wf = this;
        Object.values(this.nodes).forEach((node) => {
            node.destroy();
            wf.remove_node(node);
        });
    }
    rectify_workflow_outputs() {
        // Find out if we're using workflow_outputs or not.
        var using_workflow_outputs = false;
        var has_existing_pjas = false;
        Object.values(this.nodes).forEach((node) => {
            if (node.type === "tool" && node.workflow_outputs && node.workflow_outputs.length > 0) {
                using_workflow_outputs = true;
            }
            Object.values(node.post_job_actions).forEach((pja) => {
                if (pja.action_type === "HideDatasetAction") {
                    has_existing_pjas = true;
                }
            });
        });
        if (using_workflow_outputs !== false || has_existing_pjas !== false) {
            // Using workflow outputs, or has existing pjas.  Remove all PJAs and recreate based on outputs.
            Object.values(this.nodes).forEach((node) => {
                var node_changed = false;
                if (node.post_job_actions === null) {
                    node.post_job_actions = {};
                    node_changed = true;
                }
                var pjas_to_rem = [];
                Object.entries(node.post_job_actions).forEach(([pja_id, pja]) => {
                    if (pja.action_type == "HideDatasetAction") {
                        pjas_to_rem.push(pja_id);
                    }
                });
                if (pjas_to_rem.length > 0) {
                    pjas_to_rem.forEach((pja_name) => {
                        node_changed = true;
                        delete node.post_job_actions[pja_name];
                    });
                }
                if (using_workflow_outputs) {
                    Object.values(node.output_terminals).forEach((ot) => {
                        var create_pja = !node.isWorkflowOutput(ot.name);
                        if (create_pja === true) {
                            node_changed = true;
                            var pja = {
                                action_type: "HideDatasetAction",
                                output_name: ot.name,
                                action_arguments: {},
                            };
                            node.post_job_actions[`HideDatasetAction${ot.name}`] = null;
                            node.post_job_actions[`HideDatasetAction${ot.name}`] = pja;
                        }
                    });
                }
                // lastly, if this is the active node, and we made changes, reload the display at right.
                if (this.active_node == node && node_changed === true) {
                    this.reload_active_node();
                }
            });
        }
    }
    to_simple() {
        var nodes = {};
        Object.values(this.nodes).forEach((node) => {
            var input_connections = {};
            Object.values(node.input_terminals).forEach((t) => {
                input_connections[t.name] = null;
                // There should only be 0 or 1 connectors, so this is
                // really a sneaky if statement
                var cons = [];
                t.connectors.forEach((c, i) => {
                    if (c.handle1) {
                        var con_dict = {
                            id: c.handle1.node.id,
                            output_name: c.handle1.name,
                        };
                        var input_subworkflow_step_id = t.attributes.input.input_subworkflow_step_id;
                        if (input_subworkflow_step_id !== undefined) {
                            con_dict.input_subworkflow_step_id = input_subworkflow_step_id;
                        }
                        cons[i] = con_dict;
                        input_connections[t.name] = cons;
                    }
                });
            });
            var post_job_actions = {};
            if (node.post_job_actions) {
                Object.values(node.post_job_actions).forEach((act) => {
                    const pja = {
                        action_type: act.action_type,
                        output_name: act.output_name,
                        action_arguments: act.action_arguments,
                    };
                    post_job_actions[act.action_type + act.output_name] = null;
                    post_job_actions[act.action_type + act.output_name] = pja;
                });
            }
            if (!node.workflow_outputs) {
                node.workflow_outputs = [];
                // Just in case.
            }
            var node_data = {
                id: node.id,
                type: node.type,
                content_id: node.content_id,
                tool_version: node.config_form ? node.config_form.version : null,
                tool_state: node.tool_state,
                errors: node.errors,
                input_connections: input_connections,
                position: $(node.element).position(),
                annotation: node.annotation,
                post_job_actions: node.post_job_actions,
                uuid: node.uuid,
                label: node.label,
                workflow_outputs: node.workflow_outputs,
            };
            nodes[node.id] = node_data;
        });
        const report = this.report;
        return { steps: nodes, report: report };
    }
    from_simple(data, initialImport = true) {
        var wf = this;
        var offset = 0;
        if (initialImport) {
            wf.name = data.name;
        } else {
            offset = Object.keys(wf.nodes).length;
        }
        var max_id = offset;
        // First pass, nodes
        var using_workflow_outputs = false;
        wf.workflow_version = data.version;
        wf.report = data.report || {};
        Object.entries(data.steps).forEach(([id, step]) => {
            var node = wf.prebuildNode(step.type, step.name, step.content_id);
            // If workflow being copied into another, wipe UUID and let
            // Galaxy assign new ones.
            if (!initialImport) {
                step.uuid = null;
                step.workflow_outputs.forEach((workflow_output) => {
                    workflow_output.uuid = null;
                });
            }
            node.init_field_data(step);
            if (step.position) {
                node.element.css({
                    top: step.position.top,
                    left: step.position.left,
                });
            }
            node.id = parseInt(step.id) + offset;
            node.element.attr("id", `wf-node-step-${node.id}`);
            node.element.attr("node-label", step.label);
            wf.nodes[node.id] = node;
            max_id = Math.max(max_id, parseInt(id) + offset);
            // For older workflows, it's possible to have HideDataset PJAs, but not WorkflowOutputs.
            // Check for either, and then add outputs in the next pass.
            if (!using_workflow_outputs) {
                if (node.workflow_outputs.length > 0) {
                    using_workflow_outputs = true;
                } else {
                    Object.values(node.post_job_actions).forEach((pja) => {
                        if (pja.action_type === "HideDatasetAction") {
                            using_workflow_outputs = true;
                        }
                    });
                }
            }
        });
        wf.id_counter = max_id + 1;
        // Second pass, connections
        Object.entries(data.steps).forEach(([id, step]) => {
            const node = wf.nodes[parseInt(id) + offset];
            Object.entries(step.input_connections).forEach(([k, v]) => {
                if (v) {
                    if (!Array.isArray(v)) {
                        v = [v];
                    }
                    v.forEach((x) => {
                        const other_node = wf.nodes[parseInt(x.id) + offset];
                        const c = new Connector(this.canvas_manager);
                        c.connect(other_node.output_terminals[x.output_name], node.input_terminals[k]);
                        c.redraw();
                    });
                }
            });
            if (using_workflow_outputs) {
                // Ensure that every output terminal has a WorkflowOutput or HideDatasetAction.
                Object.values(node.output_terminals).forEach((ot) => {
                    if (node.post_job_actions[`HideDatasetAction${ot.name}`] === undefined) {
                        node.addWorkflowOutput(ot.name);
                        node.markWorkflowOutput(ot.name);
                        wf.has_changes = true;
                    }
                });
            }
        });
    }
    reload_active_node() {
        if (this.active_node) {
            var node = this.active_node;
            this.clear_active_node();
            this.activate_node(node);
        }
    }
    clear_active_node() {
        if (this.active_node) {
            this.active_node.make_inactive();
            this.active_node = null;
        }
        document.activeElement.blur();
        this.emit("onClearActiveNode");
    }
    activate_node(node) {
        if (this.active_node != node) {
            this.clear_active_node();
            node.make_active();
            this.active_node = node;
        }
        this.emit("onActiveNode", node);
    }
    node_changed(node) {
        this.has_changes = true;
        this.emit("onNodeChange", node);
    }
    scroll_to_nodes() {
        var cv = $("#canvas-viewport");
        var cc = $("#canvas-container");
        var top;
        var left;
        if (cc.width() < cv.width()) {
            left = (cv.width() - cc.width()) / 2;
        } else {
            left = 0;
        }
        if (cc.height() < cv.height()) {
            top = (cv.height() - cc.height()) / 2;
        } else {
            top = 0;
        }
        cc.css({ left: left, top: top });
    }
    layout_auto() {
        this.layout();
        this.fit_canvas_to_nodes();
        this.scroll_to_nodes();
        this.canvas_manager.draw_overview();
    }
    layout() {
        this.has_changes = true;
        // Prepare predecessor / successor tracking
        var n_pred = {};
        var successors = {};
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
            Object.values(node.input_terminals).forEach((t) => {
                t.connectors.forEach((c) => {
                    // A connection exists from `other` to `node`
                    var other = c.handle1.node;
                    // node gains a predecessor
                    n_pred[node.id] += 1;
                    // other gains a successor
                    successors[other.id].push(node.id);
                });
            });
        });
        // Assemble order, tracking levels
        var node_ids_by_level = [];
        for (;;) {
            // Everything without a predecessor
            var level_parents = [];
            for (var pred_k in n_pred) {
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
            for (var k in level_parents) {
                var v = level_parents[k];
                delete n_pred[v];
                for (var sk in successors[v]) {
                    n_pred[successors[v][sk]] -= 1;
                }
            }
        }
        if (n_pred.length) {
            // ERROR: CYCLE! Currently we do nothing
            return;
        }
        // Layout each level
        var all_nodes = this.nodes;
        var h_pad = 80;
        var v_pad = 30;
        var left = h_pad;
        node_ids_by_level.forEach((ids) => {
            // We keep nodes in the same order in a level to give the user
            // some control over ordering
            ids.sort((a, b) => $(all_nodes[a].element).position().top - $(all_nodes[b].element).position().top);
            // Position each node
            var max_width = 0;
            var top = v_pad;
            ids.forEach((id) => {
                var node = all_nodes[id];
                var element = $(node.element);
                $(element).css({ top: top, left: left });
                max_width = Math.max(max_width, $(element).width());
                top += $(element).height() + v_pad;
            });
            left += max_width + h_pad;
        });
        // Need to redraw all connectors
        Object.values(all_nodes).forEach((node) => {
            node.redraw();
        });
    }
    bounds_for_all_nodes() {
        var xmin = Infinity;
        var xmax = -Infinity;
        var ymin = Infinity;
        var ymax = -Infinity;
        var p;
        Object.values(this.nodes).forEach((node) => {
            var e = $(node.element);
            p = e.position();
            xmin = Math.min(xmin, p.left);
            xmax = Math.max(xmax, p.left + e.width());
            ymin = Math.min(ymin, p.top);
            ymax = Math.max(ymax, p.top + e.width());
        });
        return { xmin: xmin, xmax: xmax, ymin: ymin, ymax: ymax };
    }
    fit_canvas_to_nodes() {
        // Math utils
        function round_up(x, n) {
            return Math.ceil(x / n) * n;
        }
        function fix_delta(x, n) {
            if (x < n || x > 3 * n) {
                var new_pos = (Math.ceil((x % n) / n) + 1) * n;
                return -(x - new_pos);
            }
            return 0;
        }
        // Span of all elements
        var canvasZoom = this.canvas_manager.canvasZoom;
        var bounds = this.bounds_for_all_nodes();
        var position = this.canvas_container.position();
        var parent = this.canvas_container.parent();
        // Determine amount we need to expand on top/left
        var xmin_delta = fix_delta(bounds.xmin, 100);
        var ymin_delta = fix_delta(bounds.ymin, 100);
        // May need to expand farther to fill viewport
        xmin_delta = Math.max(xmin_delta, position.left);
        ymin_delta = Math.max(ymin_delta, position.top);
        var left = position.left - xmin_delta;
        var top = position.top - ymin_delta;
        // Same for width/height
        var width = round_up(bounds.xmax + 100, 100) + xmin_delta;
        var height = round_up(bounds.ymax + 100, 100) + ymin_delta;
        width = Math.max(width, -left + parent.width());
        height = Math.max(height, -top + parent.height());
        // Grow the canvas container
        this.canvas_container.css({
            left: left / canvasZoom,
            top: top / canvasZoom,
            width: width,
            height: height,
        });
        // Move elements back if needed
        this.canvas_container.children().each(function () {
            var p = $(this).position();
            $(this).css("left", (p.left + xmin_delta) / canvasZoom);
            $(this).css("top", (p.top + ymin_delta) / canvasZoom);
        });
    }
}

export default Workflow;
