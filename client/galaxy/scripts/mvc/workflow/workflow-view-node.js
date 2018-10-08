import * as _ from "libs/underscore";
import TerminalViews from "mvc/workflow/workflow-view-terminals";
import DataViews from "mvc/workflow/workflow-view-data";
export default Backbone.View.extend({
    initialize: function(options) {
        this.node = options.node;
        this.output_width = Math.max(150, this.$el.width());
        this.tool_body = this.$el.find(".toolFormBody");
        this.tool_body.find("div").remove();
        this.newInputsDiv().appendTo(this.tool_body);
        this.terminalViews = {};
        this.outputViews = {};
    },

    render: function() {
        this.renderToolLabel();
        this.renderToolErrors();
        this.$el.css("width", Math.min(250, Math.max(this.$el.width(), this.output_width)));
    },

    renderToolLabel: function() {
        this.$(".nodeTitle").text(this.node.label || this.node.name);
        this.$el.attr("node-label", this.node.label);
    },

    renderToolErrors: function() {
        this.node.errors ? this.$el.addClass("tool-node-error") : this.$el.removeClass("tool-node-error");
    },

    newInputsDiv: function() {
        return $("<div/>").addClass("inputs");
    },

    updateMaxWidth: function(newWidth) {
        this.output_width = Math.max(this.output_width, newWidth);
    },

    addRule: function() {
        this.tool_body.append($("<div/>").addClass("rule"));
    },

    addDataInput: function(input, body) {
        var skipResize = true;
        if (!body) {
            body = this.$(".inputs");
            // initial addition to node - resize input to help calculate node
            // width.
            skipResize = false;
        }
        var terminalView = this.terminalViews[input.name];
        var terminalViewClass =
            input.input_type == "dataset_collection"
                ? TerminalViews.InputCollectionTerminalView
                : TerminalViews.InputTerminalView;
        if (terminalView && !(terminalView instanceof terminalViewClass)) {
            terminalView.el.terminal.destroy();
            terminalView = null;
        }
        if (!terminalView) {
            terminalView = new terminalViewClass({
                node: this.node,
                input: input
            });
        } else {
            var terminal = terminalView.el.terminal;
            terminal.update(input);
            terminal.destroyInvalidConnections();
        }
        this.terminalViews[input.name] = terminalView;
        var terminalElement = terminalView.el;
        var inputView = new DataViews.DataInputView({
            terminalElement: terminalElement,
            input: input,
            nodeView: this,
            skipResize: skipResize
        });
        var ib = inputView.$el;
        body.append(ib.prepend(terminalView.terminalElements()));
        return terminalView;
    },

    addParameterInput: function(input, body) {
        var skipResize = true;
        if (!body) {
            body = this.$(".inputs");
            // initial addition to node - resize input to help calculate node
            // width.
            skipResize = false;
        }
        var terminalView = this.terminalViews[input.name];
        var terminalViewClass = TerminalViews.InputParameterTerminalView;
        if (terminalView && !(terminalView instanceof terminalViewClass)) {
            terminalView.el.terminal.destroy();
            terminalView = null;
        }
        if (!terminalView) {
            terminalView = new terminalViewClass({
                node: this.node,
                input: input
            });
        } else {
            var terminal = terminalView.el.terminal;
            terminal.update(input);
            terminal.destroyInvalidConnections();
        }
        this.terminalViews[input.name] = terminalView;
        var terminalElement = terminalView.el;
        var inputView = new DataViews.DataInputView({
            terminalElement: terminalElement,
            input: input,
            nodeView: this,
            skipResize: skipResize
        });
        var ib = inputView.$el;
        body.append(ib.prepend(terminalView.terminalElements()));
        return terminalView;
    },

    addDataOutput: function(output) {
        var terminalViewClass = output.collection
            ? TerminalViews.OutputCollectionTerminalView
            : TerminalViews.OutputTerminalView;
        var terminalView = new terminalViewClass({
            node: this.node,
            output: output
        });
        var outputView = new DataViews.DataOutputView({
            output: output,
            terminalElement: terminalView.el,
            nodeView: this
        });
        this.outputViews[output.name] = outputView;
        this.tool_body.append(outputView.$el.append(terminalView.terminalElements()));
    },

    addParameterOutput: function(input_parameter) {
        var terminalViewClass = TerminalViews.OutputParameterTerminalView;
        var terminalView = new terminalViewClass({
            node: this.node,
            output: input_parameter,
        });
        var parameterView = new DataViews.ParameterOutputView({
            output: input_parameter,
            terminalElement: terminalView.el,
            nodeView: this
        });
        this.outputViews[input_parameter.name] = parameterView;
        this.tool_body.append(parameterView.$el.append(terminalView.terminalElements()));
    },

    redrawWorkflowOutputs: function() {
        _.each(this.outputViews, outputView => {
            outputView.redrawWorkflowOutput();
        });
    },

    updateDataOutput: function(output) {
        var outputTerminal = this.node.output_terminals[output.name];
        outputTerminal.update(output);
    }
});
