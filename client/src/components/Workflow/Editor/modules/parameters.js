import Utils from "utils/utils";

class UntypedParameterReference {
    constructor(parameter, node) {
        parameter.references.push(this);
        this.nodeId = node.id;
    }
}

class ToolInputUntypedParameterReference extends UntypedParameterReference {
    constructor(parameter, node, tooInput) {
        super(parameter, node);
        this.toolInput = tooInput;
    }
}

class PjaUntypedParameterReference extends UntypedParameterReference {
    constructor(parameter, node, pja) {
        super(parameter, node);
        this.pja = pja;
    }
}

class UntypedParameter {
    constructor(name) {
        this.name = name;
        this.references = [];
    }

    canExtract() {
        // Backend will indicate errors but would be a bit better to pre-check for them
        // in a future iteration.
        // return false if mixed input types or if say integers are used in PJA?
        return true;
    }
}

export class UntypedParameters {
    constructor() {
        this.parameters = [];
    }

    getParameter(name) {
        for (const parameter of this.parameters) {
            if (parameter.name == name) {
                return parameter;
            }
        }
        const untypedParameter = new UntypedParameter(name);
        this.parameters.push(untypedParameter);
        return untypedParameter;
    }

    getParameterFromMatch(match) {
        return this.getParameter(match.substring(2, match.length - 1));
    }
}

export function getUntypedWorkflowParameters(nodes) {
    const untypedParameters = new UntypedParameters();
    const parameter_re = /\$\{.+?\}/g;
    Object.entries(nodes).forEach(([k, node]) => {
        if (node.config_form && node.config_form.inputs) {
            Utils.deepeach(node.config_form.inputs, (d) => {
                if (typeof d.value == "string") {
                    var form_matches = d.value.match(parameter_re);
                    if (form_matches) {
                        for (const match of form_matches) {
                            const untypedParameter = untypedParameters.getParameterFromMatch(match);
                            new ToolInputUntypedParameterReference(untypedParameter, node, d);
                        }
                    }
                }
            });
        }
        if (node.postJobActions) {
            Object.values(node.postJobActions).forEach((pja) => {
                if (pja.action_arguments) {
                    Object.values(pja.action_arguments).forEach((action_argument) => {
                        if (typeof action_argument === "string") {
                            const arg_matches = action_argument.match(parameter_re);
                            if (arg_matches) {
                                for (const match of arg_matches) {
                                    const untypedParameter = untypedParameters.getParameterFromMatch(match);
                                    new PjaUntypedParameterReference(untypedParameter, node, pja);
                                }
                            }
                        }
                    });
                }
            });
        }
    });
    return untypedParameters;
}
