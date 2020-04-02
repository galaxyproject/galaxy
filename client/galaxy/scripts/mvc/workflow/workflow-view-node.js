import $ from "jquery";
import { mountWorkflowNodeInput } from "components/Workflow/Editor/mount";

export class NodeView {
    constructor(app, options) {
        this.app = app;
        this.$el = options.$el;
        this.node = options.node;
        this.node_body = this.$el.find(".node-body");
        this.newInputsDiv().appendTo(this.node_body);
        this.outputViews = {};
    }

    render() {
        this.renderLabel();
        this.renderErrors();
    }

    renderLabel() {
        this.$el.find(".node-title").text(this.node.label || this.node.name);
        this.$el.attr("node-label", this.node.label);
    }

    renderErrors() {
        if (this.node.errors) {
            this.$el.addClass("node-error");
            this.node_body.text(this.node.errors);
        } else {
            this.$el.removeClass("node-error");
        }
    }

    newInputsDiv() {
        return $("<div/>").addClass("inputs");
    }

    addRule() {
        this.node_body.append($("<div/>").addClass("rule"));
    }

    addDataInput(input, body) {
        if (!body) {
            body = this.$el.find(".inputs");
        }
        let terminal = this.node.input_terminals[input.name];
        /*if (terminal) {
            terminal.update(input);
            terminal.destroyInvalidConnections();
            return;
        }*/
        const container = document.createElement("div");
        body.append(container);
        const nodeInput = mountWorkflowNodeInput(container, {
            input: input,
            getNode: () => {
                return this.node;
            },
            getManager: () => {
                return this.app;
            }
        });
        this.node.input_terminals[input.name] = nodeInput.terminal;
        return terminal;
    }

    addDataOutput(output) {
        return;
    }

    updateDataOutput(output) {
        var outputTerminal = this.node.output_terminals[output.name];
        outputTerminal.update(output);
    }
}
