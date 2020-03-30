import $ from "jquery";
import TerminalViews from "mvc/workflow/workflow-view-terminals";
import { mountWorkflowNodeInput, mountWorkflowNodeOutput } from "components/Workflow/Editor/mount";

export class NodeView {
    constructor(app, options) {
        this.app = app;
        this.$el = options.$el;
        this.node = options.node;
        this.node_body = this.$el.find(".node-body");
        this.node_body.find("div").remove();
        this.newInputsDiv().appendTo(this.node_body);
        this.terminalViews = {};
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
        var terminalView = this.terminalViews[input.name];
        var terminalViewClass = TerminalViews.InputTerminalView;
        if (input.input_type == "dataset_collection") {
            terminalViewClass = TerminalViews.InputCollectionTerminalView;
        } else if (input.input_type == "parameter") {
            terminalViewClass = TerminalViews.InputParameterTerminalView;
        }
        if (terminalView && !(terminalView instanceof terminalViewClass)) {
            terminalView.terminal.destroy();
            terminalView = null;
        }
        if (terminalView) {
            var terminal = terminalView.terminal;
            terminal.update(input);
            terminal.destroyInvalidConnections();
            return;
        }
        const container = document.createElement("div");
        body.prepend(container);
        const nodeInput = mountWorkflowNodeInput(container, {
            input: input,
            manager: this.app,
        });
        const terminalViewEl = nodeInput.$refs.terminal;
        terminalView = new terminalViewClass(this.app, {
            node: this.node,
            input: input,
            el: terminalViewEl
        });
        this.terminalViews[input.name] = terminalView;
    }

    terminalViewForOutput(output) {
        let terminalViewClass = TerminalViews.OutputTerminalView;
        if (output.collection) {
            terminalViewClass = TerminalViews.OutputCollectionTerminalView;
        } else if (output.parameter) {
            terminalViewClass = TerminalViews.OutputParameterTerminalView;
        }
        return new terminalViewClass(this.app, {
            node: this.node,
            output: output,
        });
    }

    addDataOutput(output) {
        const terminalView = this.terminalViewForOutput(output);
        let label = output.label || output.name;
        const showExtensions =
            output.extensions && output.extensions.length > 0 && output.extensions.indexOf("input") == -1;
        if (showExtensions) {
            const datatype = output.force_datatype || output.extensions.join(", ");
            label = `${label} (${datatype})`;
        }
        const outputView = {
            output: output,
            terminalElement: terminalView.el,
            label: label,
        };
        this.outputViews[output.name] = outputView;
        const $outputView = $(`<div class="form-row dataRow"/>`);
        $outputView.html(outputView.label);
        if (["tool", "subworkflow"].indexOf(this.node.type) >= 0) {
            const container = document.createElement("div");
            $outputView.prepend(container);
            mountWorkflowNodeOutput(container, {
                outputName: output.name,
                node: this.node,
                manager: this.app,
            });
        }
        this.node_body.append($outputView.append(terminalView.el));
    }

    updateDataOutput(output) {
        var outputTerminal = this.node.output_terminals[output.name];
        outputTerminal.update(output);
    }
}
