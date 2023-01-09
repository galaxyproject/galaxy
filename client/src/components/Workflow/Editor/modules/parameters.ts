import type { Step, Steps, PostJobAction } from "@/stores/workflowStepStore";
import Utils from "@/utils/utils";

class UntypedParameterReference {
    stepId: number;

    constructor(parameter: UntypedParameter, step: Step) {
        parameter.references.push(this);
        this.stepId = step.id;
    }
}

class ToolInputUntypedParameterReference extends UntypedParameterReference {
    // TODO: replace any when we have a defined tool state
    toolInput: any;

    constructor(parameter: UntypedParameter, step: Step, toolInput: any) {
        super(parameter, step);
        this.toolInput = toolInput;
    }
}

class PjaUntypedParameterReference extends UntypedParameterReference {
    pja: PostJobAction;

    constructor(parameter: UntypedParameter, step: Step, pja: PostJobAction) {
        super(parameter, step);
        this.pja = pja;
    }
}

type UntypedParameterReferenceTypes =
    | UntypedParameterReference
    | ToolInputUntypedParameterReference
    | PjaUntypedParameterReference;

class UntypedParameter {
    name: string;
    references: UntypedParameterReferenceTypes[];

    constructor(name: string) {
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
    parameters: UntypedParameter[];

    constructor() {
        this.parameters = [];
    }

    getParameter(name: string) {
        for (const parameter of this.parameters) {
            if (parameter.name == name) {
                return parameter;
            }
        }
        const untypedParameter = new UntypedParameter(name);
        this.parameters.push(untypedParameter);
        return untypedParameter;
    }

    getParameterFromMatch(match: string) {
        return this.getParameter(match.substring(2, match.length - 1));
    }
}

export function getUntypedWorkflowParameters(steps: Steps) {
    const untypedParameters = new UntypedParameters();
    const parameter_re = /\$\{.+?\}/g;
    Object.values(steps).forEach((step) => {
        if (step.config_form?.inputs) {
            // TODO: with new tool state we could type this and drop the any
            Utils.deepeach(step.config_form.inputs, (d: any) => {
                if (typeof d.value == "string") {
                    const formMatches = d.value.match(parameter_re);
                    if (formMatches) {
                        for (const match of formMatches) {
                            const untypedParameter = untypedParameters.getParameterFromMatch(match);
                            new ToolInputUntypedParameterReference(untypedParameter, step, d);
                        }
                    }
                }
            });
        }
        if (step.post_job_actions) {
            Object.values(step.post_job_actions).forEach((pja) => {
                if (pja.action_arguments) {
                    Object.values(pja.action_arguments).forEach((action_argument) => {
                        if (typeof action_argument === "string") {
                            const arg_matches = action_argument.match(parameter_re);
                            if (arg_matches) {
                                for (const match of arg_matches) {
                                    const untypedParameter = untypedParameters.getParameterFromMatch(match);
                                    new PjaUntypedParameterReference(untypedParameter, step, pja);
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
