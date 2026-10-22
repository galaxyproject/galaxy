import type { PostJobAction, Step, Steps } from "@/stores/workflowStepStore";
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

export class UntypedParameter {
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
}

const REPLACEMENT_PARAMETER_RE = /\$\{(.+?)\}/g;

/** Names of the `${name}` replacement parameters in a string. */
function replacementParameterNames(value: string): string[] {
    return Array.from(value.matchAll(REPLACEMENT_PARAMETER_RE), (match) => match[1]!);
}

export function getUntypedWorkflowParameters(steps: Steps) {
    const untypedParameters = new UntypedParameters();
    Object.values(steps).forEach((step) => {
        if (step.config_form?.inputs) {
            // TODO: with new tool state we could type this and drop the any
            Utils.deepEach(step.config_form.inputs, (d: any) => {
                if (typeof d.value == "string") {
                    for (const name of replacementParameterNames(d.value)) {
                        new ToolInputUntypedParameterReference(untypedParameters.getParameter(name), step, d);
                    }
                }
            });
        }
        Object.values(step.post_job_actions ?? {}).forEach((pja) => {
            Object.values(pja.action_arguments ?? {}).forEach((actionArgument) => {
                if (typeof actionArgument === "string") {
                    for (const name of replacementParameterNames(actionArgument)) {
                        new PjaUntypedParameterReference(untypedParameters.getParameter(name), step, pja);
                    }
                }
            });
        });
    });
    return untypedParameters;
}
