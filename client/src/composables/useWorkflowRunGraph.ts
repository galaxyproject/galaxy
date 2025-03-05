import { faCheckCircle, faExclamationCircle, faSpinner, type IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { computed, type Ref, ref } from "vue";

import { isWorkflowInput } from "@/components/Workflow/constants";
import { fromSimple } from "@/components/Workflow/Editor/modules/model";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { type Step } from "@/stores/workflowStepStore";
import { rethrowSimple } from "@/utils/simple-error";

import { getHeaderClass } from "./useInvocationGraph";

const STEP_DESCRIPTIONS = {
    TextToolParameter: "Provide text input",
    IntegerToolParameter: "Provide an integer",
    FloatToolParameter: "Provide a float",
    ColorToolParameter: "Provide a color",
    DirectoryUriToolParameter: "Provide a directory",
    DataToolParameter: "Provide a dataset",
    DataCollectionToolParameter: "Provide a collection",
    SelectToolParameter: "Select an option",
    BooleanToolParameter: "",
};

interface BaseDataToolParameterInput {
    batch: boolean;
    product: boolean;
    values: { id: string; src: "dce" | "hda" | "hdca" | "ldda"; map_over_type: string }[];
}
interface DataToolParameterInput extends BaseDataToolParameterInput {}
interface DataCollectionToolParameterInput extends BaseDataToolParameterInput {}
export type DataInput = DataToolParameterInput | DataCollectionToolParameterInput | boolean | string | null;

interface WorkflowRunStepInfo {
    headerClass?: Record<string, boolean>;
    headerIcon?: IconDefinition;
    headerIconSpin?: boolean;
    nodeText?: string | boolean;
}

interface WorkflowRunStep extends Readonly<Step>, WorkflowRunStepInfo {}

/** Composable that creates a readonly workflow run graph and loads it onto a workflow editor canvas for display.
 * This graph updates as the user changes the inputs of the workflow.
 * @param workflowId - The id of the workflow
 * @param workflowVersion - The version of the workflow
 * @param inputs - The current inputs of the workflow
 * @param formInputs - The form inputs of the workflow
 * @param stepValidation - The current error if any at the stepId: [stepId, message]
 */
export function useWorkflowRunGraph(
    workflowId: string | undefined,
    workflowVersion: number | undefined,
    inputs: Ref<Record<string, DataInput | null>>,
    formInputs: Ref<any[]>,
    stepValidation: Ref<[string, string] | undefined>
) {
    /** The workflow that is to be run */
    const loadedWorkflow = ref<any>(null);

    const loading = ref(true);

    async function loadWorkflowOntoGraph() {
        loading.value = true;

        try {
            if (!workflowId) {
                throw new Error("Workflow Id is not defined");
            }
            if (workflowVersion === undefined) {
                throw new Error("Workflow Version is not defined");
            }

            // initialize the original full workflow ref
            if (!loadedWorkflow.value) {
                loadedWorkflow.value = await getWorkflowFull(workflowId, workflowVersion);
            }

            await fromSimple(workflowId, loadedWorkflow.value);
        } catch (e) {
            rethrowSimple(e);
        } finally {
            loading.value = false;
        }
    }

    /** The steps of the original workflow */
    const workflowSteps = computed<Record<string, Readonly<Step>>>(() => loadedWorkflow.value?.steps);

    const steps = computed<Record<string, WorkflowRunStep>>(() => {
        if (!workflowSteps.value || !formInputs.value || !inputs.value) {
            return {};
        }

        const result: Record<string, WorkflowRunStep> = {};
        for (const stepId in workflowSteps.value) {
            const step = workflowSteps.value[stepId];
            if (step) {
                let stepInfo: WorkflowRunStepInfo | null = null;
                const validation = getWorkflowRunStepValidation(step);
                if (validation) {
                    stepInfo = validation;
                } else if (isWorkflowInput(step.type)) {
                    const dataInput = inputs.value[step.id.toString()];
                    const formInput = formInputs.value.find((input) => parseInt(input.name) === step.id);
                    stepInfo = getWorkflowRunStepInfo(formInput, dataInput);
                }
                if (stepInfo) {
                    result[stepId] = { ...step, ...stepInfo };
                }
            }
        }
        return result;
    });

    /** Return step desciptions for the workflow graph given the current input field and user value
     * @param formInput The form input field
     * @param dataInput The user input value
     */
    function getWorkflowRunStepInfo(formInput: any, dataInput?: DataInput): WorkflowRunStepInfo {
        const optional = formInput?.optional as boolean;
        const modelClass = formInput?.model_class as keyof typeof STEP_DESCRIPTIONS;

        if (modelClass === "BooleanToolParameter") {
            return getStepDescription(dataInput as boolean, true);
        } else if (modelClass === "DataToolParameter" || modelClass === "DataCollectionToolParameter") {
            dataInput = dataInput as DataToolParameterInput | DataCollectionToolParameterInput;
            const inputVals = dataInput?.values;
            const options = formInput?.options;

            if (inputVals?.length === 1 && inputVals[0]) {
                const { id, src } = inputVals[0];
                const item = options[src].find((option: any) => option.id === id);

                if (item && item.hid && item.name) {
                    return getStepDescription(`${item.hid}: <b>${item.name}</b>`, true);
                } else {
                    return getStepDescription("Input value processing", true, optional, true);
                }
            } else if (inputVals?.length) {
                return getStepDescription(`${inputVals.length} inputs provided`, true);
            } else {
                return getStepDescription(STEP_DESCRIPTIONS[modelClass], false, optional);
            }
        } else if (Object.keys(STEP_DESCRIPTIONS).includes(modelClass)) {
            if (!dataInput || dataInput.toString().trim() === "") {
                return getStepDescription(STEP_DESCRIPTIONS[modelClass], false, optional);
            } else {
                let text: string;
                switch (modelClass) {
                    case "ColorToolParameter":
                        text = dataInput as string;
                        break;
                    case "DirectoryUriToolParameter":
                        text = `Directory: <b>${dataInput}</b>`;
                        break;
                    default:
                        text = `<b>${dataInput}</b>`;
                }
                return getStepDescription(text, true);
            }
        } else {
            return getStepDescription("This is an input", true);
        }
    }

    /** Return step desciptions for the workflow graph given the current input value or prompt
     * @param text The text to display
     * @param populated Whether the input is populated, undefined for optional inputs
     * @param optional Whether the input is optional
     * @param spin Whether the icon should spin
     */
    function getStepDescription(
        text: string | boolean,
        populated: boolean,
        optional?: boolean,
        spin?: boolean
    ): WorkflowRunStepInfo {
        // color variant for `paused` state works best for unpopulated inputs,
        // "" for optional inputs and `ok` for populated inputs
        const headerClass = optional ? "" : !spin && populated ? "ok" : "paused";
        const headerIcon = spin ? faSpinner : populated ? faCheckCircle : faExclamationCircle;

        text = typeof text === "boolean" ? text : !optional ? text : `${text} (optional)`;

        return {
            nodeText: text,
            headerClass: getHeaderClass(headerClass),
            headerIcon,
            headerIconSpin: spin,
        };
    }

    function getWorkflowRunStepValidation(step: Step): WorkflowRunStepInfo | null {
        if (stepValidation.value && stepValidation.value.length == 2) {
            const [stepId, message] = stepValidation.value;

            if (stepId === step.id.toString()) {
                const text = message.length < 20 ? message : "Fix error(s) for this step";
                return getStepDescription(text, false);
            }
        }
        return null;
    }

    return {
        /** The steps of the workflow run graph */
        steps,
        /** Fetches the original workflow structure and loads it onto the graph */
        loadWorkflowOntoGraph,
        loading,
    };
}
