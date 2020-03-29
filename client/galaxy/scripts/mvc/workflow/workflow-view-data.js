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
        this.label = output.label || output.name;
        const isInput = output.extensions.indexOf("input") >= 0;
        const datatype = output.force_datatype || output.extensions.join(", ");
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
