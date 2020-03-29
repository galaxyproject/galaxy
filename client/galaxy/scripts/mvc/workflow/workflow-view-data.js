import $ from "jquery";

export class DataInputView {
    constructor(options = {}) {
        this.input = options.input;
        this.terminalElement = options.terminalElement;
        const input = options.input;
        this.label = input.label || input.name;
    }
}

export class DataOutputView {
    constructor(options = {}) {
        this.output = options.output;
        this.terminalElement = options.terminalElement;
        const output = this.output;
        const isInput = output.extensions.indexOf("input") >= 0;
        const datatype = output.force_datatype || output.extensions.join(", ");
        this.label = output.label || output.name;
        if (!isInput) {
            this.label = `${this.label} (${datatype})`;
        }
    }
}

export class ParameterOutputView {
    constructor(options = {}) {
        this.output = options.output;
        this.terminalElement = options.terminalElement;
        const output = this.output;
        this.label = output.label || output.name;
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
