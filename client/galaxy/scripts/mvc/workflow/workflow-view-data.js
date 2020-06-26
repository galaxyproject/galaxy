import $ from "jquery";

export class DataInputView {
    constructor(options = {}) {
        this.input = options.input;
        this.nodeView = options.nodeView;
        this.terminalElement = options.terminalElement;
        this.$el = $(`<div class="form-row dataRow input-data-row"/>`);
        this.$el.attr("name", this.input.name).html(this.input.label || this.input.name);
        if (!options.skipResize) {
            this.$el.css({
                position: "absolute",
                left: -1000,
                top: -1000,
                display: "none",
            });
            $("body").append(this.el);
            this.nodeView.updateMaxWidth(this.$el.outerWidth());
            this.$el.css({
                position: "",
                left: "",
                top: "",
                display: "",
            });
            this.$el.remove();
        }
    }
}

export class DataOutputView {
    constructor(app, options = {}) {
        this.$el = $(`<div class="form-row dataRow"/>`);
        this.output = options.output;
        this.terminalElement = options.terminalElement;
        this.nodeView = options.nodeView;
        const output = this.output;
        let label = output.label || output.name;
        const node = this.nodeView.node;
        const isInput = output.extensions.indexOf("input") >= 0;
        const datatype = output.force_datatype || output.extensions.join(", ");
        if (!isInput) {
            label = `${label} (${datatype})`;
        }
        this.$el.html(label);
        this.calloutView = null;
        if (["tool", "subworkflow"].indexOf(node.type) >= 0) {
            const calloutView = new OutputCalloutView(app, {
                label: label,
                output: output,
                node: node,
            });
            this.calloutView = calloutView;
            this.$el.prepend(calloutView.$el);
        }
        this.$el.css({
            position: "absolute",
            left: -1000,
            top: -1000,
            display: "none",
        });
        $("body").append(this.el);
        this.nodeView.updateMaxWidth(this.$el.outerWidth() + 17);
        this.$el
            .css({
                position: "",
                left: "",
                top: "",
                display: "",
            })
            .detach();
    }
    redrawWorkflowOutput() {
        if (this.calloutView) {
            this.calloutView.render();
        }
    }
}

export class ParameterOutputView {
    constructor(app, options = {}) {
        this.$el = $(`<div class="form-row dataRow"/>`);
        this.output = options.output;
        this.terminalElement = options.terminalElement;
        this.nodeView = options.nodeView;
        const output = this.output;
        const label = output.label || output.name;
        const node = this.nodeView.node;
        this.$el.html(label);
        this.calloutView = null;
        if (["tool", "subworkflow"].indexOf(node.type) >= 0) {
            const calloutView = new OutputCalloutView(app, {
                label: label,
                output: output,
                node: node,
            });
            this.calloutView = calloutView;
            this.$el.append(calloutView.$el);
        }
        this.$el.css({
            position: "absolute",
            left: -1000,
            top: -1000,
            display: "none",
        });
        $("body").append(this.el);
        this.nodeView.updateMaxWidth(this.$el.outerWidth() + 17);
        this.$el
            .css({
                position: "",
                left: "",
                top: "",
                display: "",
            })
            .detach();
    }
    redrawWorkflowOutput() {
        if (this.calloutView) {
            this.calloutView.render();
        }
    }
}

export class OutputCalloutView {
    constructor(app, options = {}) {
        this.$el = $("<div/>");
        this.label = options.label;
        this.node = options.node;
        this.output = options.output;
        const node = this.node;
        const outputName = this.output.name;
        this.$el
            .attr("class", `callout-terminal ${outputName}`)
            .append(
                $("<icon />")
                    .addClass("mark-terminal")
                    .click(() => {
                        if (node.isWorkflowOutput(outputName)) {
                            node.removeWorkflowOutput(outputName);
                        } else {
                            node.addWorkflowOutput(outputName);
                        }
                        this.render();
                        app.has_changes = true;
                        app.canvas_manager.draw_overview();
                    })
            )
            .tooltip({
                delay: 500,
                title: "Unchecked output datasets will be hidden.",
            });
        this.render();
    }
    render() {
        if (!this.node.isWorkflowOutput(this.output.name)) {
            this.$el.find("icon").removeClass("mark-terminal-active");
        } else {
            this.$el.find("icon").addClass("mark-terminal-active");
        }
    }
}
