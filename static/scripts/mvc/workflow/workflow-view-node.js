define("mvc/workflow/workflow-view-node", ["exports", "libs/underscore", "mvc/workflow/workflow-view-terminals", "mvc/workflow/workflow-view-data"], function(exports, _underscore, _workflowViewTerminals, _workflowViewData) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _ = _interopRequireWildcard(_underscore);

    var _workflowViewTerminals2 = _interopRequireDefault(_workflowViewTerminals);

    var _workflowViewData2 = _interopRequireDefault(_workflowViewData);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    function _interopRequireWildcard(obj) {
        if (obj && obj.__esModule) {
            return obj;
        } else {
            var newObj = {};

            if (obj != null) {
                for (var key in obj) {
                    if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key];
                }
            }

            newObj.default = obj;
            return newObj;
        }
    }

    exports.default = Backbone.View.extend({
        initialize: function initialize(options) {
            this.node = options.node;
            this.output_width = Math.max(150, this.$el.width());
            this.tool_body = this.$el.find(".toolFormBody");
            this.tool_body.find("div").remove();
            this.newInputsDiv().appendTo(this.tool_body);
            this.terminalViews = {};
            this.outputViews = {};
        },

        render: function render() {
            this.renderToolLabel();
            this.renderToolErrors();
            this.$el.css("width", Math.min(250, Math.max(this.$el.width(), this.output_width)));
        },

        renderToolLabel: function renderToolLabel() {
            this.$(".nodeTitle").text(this.node.label || this.node.name);
        },

        renderToolErrors: function renderToolErrors() {
            this.node.errors ? this.$el.addClass("tool-node-error") : this.$el.removeClass("tool-node-error");
        },

        newInputsDiv: function newInputsDiv() {
            return $("<div/>").addClass("inputs");
        },

        updateMaxWidth: function updateMaxWidth(newWidth) {
            this.output_width = Math.max(this.output_width, newWidth);
        },

        addRule: function addRule() {
            this.tool_body.append($("<div/>").addClass("rule"));
        },

        addDataInput: function addDataInput(input, body) {
            var skipResize = true;
            if (!body) {
                body = this.$(".inputs");
                // initial addition to node - resize input to help calculate node
                // width.
                skipResize = false;
            }
            var terminalView = this.terminalViews[input.name];
            var terminalViewClass = input.input_type == "dataset_collection" ? _workflowViewTerminals2.default.InputCollectionTerminalView : _workflowViewTerminals2.default.InputTerminalView;
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
            var inputView = new _workflowViewData2.default.DataInputView({
                terminalElement: terminalElement,
                input: input,
                nodeView: this,
                skipResize: skipResize
            });
            var ib = inputView.$el;
            body.append(ib.prepend(terminalView.terminalElements()));
            return terminalView;
        },

        addDataOutput: function addDataOutput(output) {
            var terminalViewClass = output.collection ? _workflowViewTerminals2.default.OutputCollectionTerminalView : _workflowViewTerminals2.default.OutputTerminalView;
            var terminalView = new terminalViewClass({
                node: this.node,
                output: output
            });
            var outputView = new _workflowViewData2.default.DataOutputView({
                output: output,
                terminalElement: terminalView.el,
                nodeView: this
            });
            this.outputViews[output.name] = outputView;
            this.tool_body.append(outputView.$el.append(terminalView.terminalElements()));
        },

        redrawWorkflowOutputs: function redrawWorkflowOutputs() {
            _.each(this.outputViews, function(outputView) {
                outputView.redrawWorkflowOutput();
            });
        },

        updateDataOutput: function updateDataOutput(output) {
            var outputTerminal = this.node.output_terminals[output.name];
            outputTerminal.update(output);
        }
    });
});
//# sourceMappingURL=../../../maps/mvc/workflow/workflow-view-node.js.map
