import _ from "underscore";
import _l from "utils/localization";
import Utils from "utils/utils";


class LegacyParameterReference {
    constructor(parameter, node) {
        parameter.references.push(this);
        this.nodeId = node.id;
    }
}

class ToolInputLegacyParameterReference extends LegacyParameterReference {
    constructor(parameter, node, tooInput) {
        super(parameter, node);
        this.toolInput = tooInput;
    }
}

class PjaLegacyParameterReference extends LegacyParameterReference {
    constructor(parameter, node, pja) {
        super(parameter, node);
        this.pja = pja;
    }
}

class LegacyParameter {
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

export class LegacyParameters {
    constructor() {
        this.parameters = [];
    }

    getParameter(name) {
        for (const parameter of this.parameters) {
            if (parameter.name == name) {
                return parameter;
            }
        }
        const legacyParameter = new LegacyParameter(name);
        this.parameters.push(legacyParameter);
        return legacyParameter;
    }

    getParameterFromMatch(match) {
        return this.getParameter(match.substring(2, match.length - 1));
    }
}

export function getLegacyWorkflowParameters(nodes) {
    const legacyParameters = new LegacyParameters();
    const parameter_re = /\$\{.+?\}/g;
    Object.entries(nodes).forEach(([k, node]) => {
        if (node.config_form && node.config_form.inputs) {
            Utils.deepeach(node.config_form.inputs, (d) => {
                if (typeof d.value == "string") {
                    var form_matches = d.value.match(parameter_re);
                    if (form_matches) {
                        for (const match of form_matches) {
                            const legacyParameter = legacyParameters.getParameterFromMatch(match);
                            new ToolInputLegacyParameterReference(legacyParameter, node, d);
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
                                    const legacyParameter = legacyParameters.getParameterFromMatch(match);
                                    new PjaLegacyParameterReference(legacyParameter, node, pja);
                                }
                            }
                        }
                    });
                }
            });
        }
    });
    return legacyParameters;
}
