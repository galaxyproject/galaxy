import $ from "jquery";
import _ from "libs/underscore";
import TerminalViews from "mvc/workflow/workflow-view-terminals";
import { DataInputView, DataOutputView, ParameterOutputView } from "mvc/workflow/workflow-view-data";

export class NodeView {
    constructor(app, options) {
        this.app = app;
        this.$el = options.$el;
        this.node = options.node;
        this.output_width = Math.max(150, this.$el.width());
        this.node_body = this.$el.find(".node-body");
        this.node_body.find("div").remove();
        this.newInputsDiv().appendTo(this.node_body);
        this.terminalViews = {};
        this.outputViews = {};
    }

    render() {
        this.renderLabel();
        this.renderErrors();
        this.$el.css("width", Math.min(250, Math.max(this.$el.width(), this.output_width)));
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

    updateMaxWidth(newWidth) {
        this.output_width = Math.max(this.output_width, newWidth);
    }

    addRule() {
        this.node_body.append($("<div/>").addClass("rule"));
    }

    addDataInput(input, body) {
        var skipResize = true;
        if (!body) {
            body = this.$el.find(".inputs");
            // initial addition to node - resize input to help calculate node
            // width.
            skipResize = false;
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
        if (!terminalView) {
            terminalView = new terminalViewClass(this.app, {
                node: this.node,
                input: input,
            });
        } else {
            var terminal = terminalView.terminal;
            terminal.update(input);
            terminal.destroyInvalidConnections();
        }
        this.terminalViews[input.name] = terminalView;
        var terminalElement = terminalView.el;
        var inputView = new DataInputView({
            terminalElement: terminalElement,
            input: input,
            nodeView: this,
            skipResize: skipResize,
        });
        var ib = inputView.$el;
        body.append(ib.prepend(terminalView.el));
        return terminalView;
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

    outputViewforOutput(output, terminalView) {
        const outputViewClass = output.parameter ? ParameterOutputView : DataOutputView;
        return new outputViewClass(this.app, {
            output: output,
            terminalElement: terminalView.el,
            nodeView: this,
        });
    }

    addDataOutput(output) {
        const terminalView = this.terminalViewForOutput(output);
        const outputView = this.outputViewforOutput(output, terminalView);
        this.outputViews[output.name] = outputView;
        this.node_body.append(outputView.$el.append(terminalView.el));
    }

    redrawWorkflowOutputs() {
        _.each(this.outputViews, (outputView) => {
            outputView.redrawWorkflowOutput();
        });
    }

    updateDataOutput(output) {
        var outputTerminal = this.node.output_terminals[output.name];
        outputTerminal.update(output);
    }
}
