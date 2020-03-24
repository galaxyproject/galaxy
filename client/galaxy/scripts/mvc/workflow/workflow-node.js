import _ from "underscore";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import Utils from "utils/utils";
import { NodeView } from "./workflow-view-node";

export class Node {
    constructor(app, attr = {}) {
        this.app = app;
        this.element = attr.element;
        this.input_terminals = {};
        this.output_terminals = {};
        this.errors = null;
        this.workflow_outputs = [];
    }
    getWorkflowOutput(outputName) {
        return _.findWhere(this.workflow_outputs, {
            output_name: outputName,
        });
    }
    isWorkflowOutput(outputName) {
        return this.getWorkflowOutput(outputName) !== undefined;
    }
    removeWorkflowOutput(outputName) {
        while (this.isWorkflowOutput(outputName)) {
            const target = this.getWorkflowOutput(outputName);
            this.workflow_outputs.splice(_.indexOf(this.workflow_outputs, target), 1);
        }
    }
    addWorkflowOutput(outputName, label) {
        if (!this.isWorkflowOutput(outputName)) {
            var output = { output_name: outputName };
            if (label) {
                output.label = label;
            }
            this.workflow_outputs.push(output);
            return true;
        }
        return false;
    }
    markWorkflowOutput(outputName) {
        var callout = $(this.element).find(`.callout-terminal.${outputName.replace(/(?=[()])/g, "\\")}`);
        callout.find("icon").addClass("mark-terminal-active");
    }
    labelWorkflowOutput(outputName, label) {
        var changed = false;
        var oldLabel = null;
        if (this.isWorkflowOutput(outputName)) {
            var workflowOutput = this.getWorkflowOutput(outputName);
            oldLabel = workflowOutput.label;
            workflowOutput.label = label;
            changed = oldLabel != label;
        } else {
            changed = this.addWorkflowOutput(outputName, label);
        }
        if (changed) {
            this.app.updateOutputLabel(oldLabel, label);
            this.markChanged();
            this.nodeView.redrawWorkflowOutputs();
        }
        return changed;
    }
    changeOutputDatatype(outputName, datatype) {
        const output_terminal = this.output_terminals[outputName];
        const output = this.nodeView.outputViews[outputName].output;
        output_terminal.force_datatype = datatype;
        output.force_datatype = datatype;
        if (datatype) {
            this.post_job_actions["ChangeDatatypeAction" + outputName] = {
                action_arguments: { newtype: datatype },
                action_type: "ChangeDatatypeAction",
                output_name: outputName,
            };
        } else {
            delete this.post_job_actions["ChangeDatatypeAction" + outputName];
        }
        this.markChanged();
        output_terminal.destroyInvalidConnections();
    }
    connectedOutputTerminals() {
        return this._connectedTerminals(this.output_terminals);
    }
    _connectedTerminals(terminals) {
        var connectedTerminals = [];
        $.each(terminals, (_, t) => {
            if (t.connectors.length > 0) {
                connectedTerminals.push(t);
            }
        });
        return connectedTerminals;
    }
    hasConnectedOutputTerminals() {
        // return this.connectedOutputTerminals().length > 0; <- optimized this
        var outputTerminals = this.output_terminals;
        for (var outputName in outputTerminals) {
            if (outputTerminals[outputName].connectors.length > 0) {
                return true;
            }
        }
        return false;
    }
    connectedMappedInputTerminals() {
        return this._connectedMappedTerminals(this.input_terminals);
    }
    hasConnectedMappedInputTerminals() {
        // return this.connectedMappedInputTerminals().length > 0; <- optimized this
        var inputTerminals = this.input_terminals;
        for (var inputName in inputTerminals) {
            var inputTerminal = inputTerminals[inputName];
            if (inputTerminal.connectors.length > 0 && inputTerminal.isMappedOver()) {
                return true;
            }
        }
        return false;
    }
    _connectedMappedTerminals(terminals) {
        var mapped_outputs = [];
        $.each(terminals, (_, t) => {
            var mapOver = t.mapOver;
            if (mapOver.isCollection) {
                if (t.connectors.length > 0) {
                    mapped_outputs.push(t);
                }
            }
        });
        return mapped_outputs;
    }
    mappedInputTerminals() {
        return this._mappedTerminals(this.input_terminals);
    }
    _mappedTerminals(terminals) {
        var mappedTerminals = [];
        $.each(terminals, (_, t) => {
            var mapOver = t.mapOver;
            if (mapOver.isCollection) {
                mappedTerminals.push(t);
            }
        });
        return mappedTerminals;
    }
    hasMappedOverInputTerminals() {
        var found = false;
        _.each(this.input_terminals, (t) => {
            var mapOver = t.mapOver;
            if (mapOver.isCollection) {
                found = true;
            }
        });
        return found;
    }
    redraw() {
        $.each(this.input_terminals, (_, t) => {
            t.redraw();
        });
        $.each(this.output_terminals, (_, t) => {
            t.redraw();
        });
    }
    clone() {
        var copiedData = {
            name: this.name,
            label: this.label,
            annotation: this.annotation,
            post_job_actions: this.post_job_actions,
        };
        var node = this.app.create_node(this.type, this.name, this.content_id);
        Utils.request({
            type: "POST",
            url: `${getAppRoot()}api/workflows/build_module`,
            data: {
                type: this.type,
                tool_id: this.content_id,
                tool_state: this.tool_state,
            },
            success: (data) => {
                var newData = Object.assign({}, data, copiedData);
                node.init_field_data(newData);
                node.update_field_data(newData);
                this.app.activate_node(node);
            },
        });
    }
    destroy() {
        $.each(this.input_terminals, (k, t) => {
            t.destroy();
        });
        $.each(this.output_terminals, (k, t) => {
            t.destroy();
        });
        this.app.remove_node(this);
        $(this.element).remove();
    }
    make_active() {
        $(this.element).addClass("node-active");
    }
    make_inactive() {
        // Keep inactive nodes stacked from most to least recently active
        // by moving element to the end of parent's node list
        var element = this.element.get(0);
        ((p) => {
            p.removeChild(element);
            p.appendChild(element);
        })(element.parentNode);
        // Remove active class
        $(element).removeClass("node-active");
    }
    set_tool_version() {
        if (this.type === "tool" && this.config_form) {
            this.tool_version = this.config_form.version;
            this.content_id = this.config_form.id;
        }
    }
    init_field_data(data) {
        //console.debug("init_field_data: ", data);
        if (data.type) {
            this.type = data.type;
        }
        this.name = data.name;
        this.config_form = data.config_form;
        this.set_tool_version();
        this.tool_state = data.tool_state;
        this.errors = data.errors;
        this.tooltip = data.tooltip ? data.tooltip : "";
        this.annotation = data.annotation;
        this.post_job_actions = data.post_job_actions ? data.post_job_actions : {};
        this.label = data.label;
        this.uuid = data.uuid;
        this.workflow_outputs = data.workflow_outputs ? data.workflow_outputs : [];
        var node = this;
        var nodeView = new NodeView(this.app, {
            $el: this.element,
            node: node,
        });
        node.nodeView = nodeView;
        $.each(data.inputs, (i, input) => {
            nodeView.addDataInput(input);
        });

        if (data.inputs.length > 0 && data.outputs.length > 0) {
            nodeView.addRule();
        }
        $.each(data.outputs, (i, output) => {
            nodeView.addDataOutput(output);
        });
        nodeView.render();
        this.app.node_changed(this);
    }
    update_field_data(data) {
        var node = this;
        var nodeView = node.nodeView;
        // remove unused output views and remove pre-existing output views from data.outputs,
        // so that these are not added twice.
        var unused_outputs = [];
        // nodeView.outputViews contains pre-existing outputs,
        // while data.data_output contains what should be displayed.
        // Now we gather the unused outputs
        $.each(nodeView.outputViews, (i, output_view) => {
            var cur_name = output_view.output.name;
            var data_names = data.outputs;
            var cur_name_in_data_outputs = false;
            _.each(data_names, (data_name) => {
                if (data_name.name == cur_name) {
                    cur_name_in_data_outputs = true;
                }
            });
            if (cur_name_in_data_outputs === false) {
                unused_outputs.push(cur_name);
            }
        });
        // Remove the unused outputs
        _.each(unused_outputs, (unused_output) => {
            _.each(nodeView.outputViews[unused_output].terminalElement.terminal.connectors, (x) => {
                if (x) {
                    x.destroy(); // Removes the noodle connectors
                }
            });
            nodeView.outputViews[unused_output].remove(); // removes the rendered output
            delete nodeView.outputViews[unused_output]; // removes the reference to the output
            delete node.output_terminals[unused_output]; // removes the output terminal
        });
        $.each(node.workflow_outputs, (i, wf_output) => {
            if (wf_output && !node.output_terminals[wf_output.output_name]) {
                node.workflow_outputs.splice(i, 1); // removes output from list of workflow outputs
            }
        });
        $.each(data.outputs, (i, output) => {
            if (!nodeView.outputViews[output.name]) {
                nodeView.addDataOutput(output); // add data output if it does not yet exist
            } else {
                // the output already exists, but the output formats may have changed.
                // Therefore we update the datatypes and destroy invalid connections.
                node.output_terminals[output.name].datatypes = output.extensions;
                node.output_terminals[output.name].force_datatype = output.force_datatype;
                if (node.type == "parameter_input") {
                    node.output_terminals[output.name].attributes.type = output.type;
                }
                node.output_terminals[output.name].optional = output.optional;
                node.output_terminals[output.name].destroyInvalidConnections();
            }
        });
        this.tool_state = data.tool_state;
        this.config_form = data.config_form;
        this.set_tool_version();
        this.errors = data.errors;
        this.annotation = data.annotation;
        this.label = data.label;
        if ("post_job_actions" in data) {
            // Won't be present in response for data inputs
            var pja_in = data.post_job_actions;
            this.post_job_actions = pja_in ? pja_in : {};
        }
        node.nodeView.renderErrors();
        // Update input rows
        var old_body = nodeView.$el.find("div.inputs");
        var new_body = nodeView.newInputsDiv();
        var newTerminalViews = {};
        _.each(data.inputs, (input) => {
            newTerminalViews[input.name] = node.nodeView.addDataInput(input, new_body);
        });
        // Cleanup any leftover terminals
        _.each(_.difference(_.values(nodeView.terminalViews), _.values(newTerminalViews)), (unusedView) => {
            unusedView.terminal.destroy();
        });
        nodeView.terminalViews = newTerminalViews;
        node.nodeView.render();
        // In general workflow editor assumes tool outputs don't change in # or
        // type (not really valid right?) but adding special logic here for
        // data collection input parameters that can have their collection
        // change.
        var data_outputs = data.outputs;
        if (data_outputs.length == 1 && "collection_type" in data_outputs[0]) {
            nodeView.updateDataOutput(data_outputs[0]);
        }
        old_body.replaceWith(new_body);
        if ("workflow_outputs" in data) {
            // Won't be present in response for data inputs
            this.workflow_outputs = data.workflow_outputs ? data.workflow_outputs : [];
        }
        // If active, reactivate with new config_form
        this.markChanged();
        this.redraw();
    }
    markChanged() {
        this.app.node_changed(this);
    }
}
