import { faCheckCircle, faExclamationCircle, type IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { computed, type Ref, ref, set } from "vue";

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

interface WorkflowRunStep extends Readonly<Step> {
    headerClass?: Record<string, boolean>;
    headerIcon?: IconDefinition;
    nodeText?: string | boolean;
}

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

    async function loadWorkflowRunGraph() {
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

    const workflowSteps = computed<Record<string, Readonly<Step>>>(() => loadedWorkflow.value?.steps);

    const steps = computed<{ [index: string]: WorkflowRunStep }>(() => {
        if (!workflowSteps.value || !formInputs.value || !inputs.value) {
            return {};
        }

        return Object.keys(workflowSteps.value).reduce((acc: { [index: string]: WorkflowRunStep }, k: string) => {
            const step = { ...workflowSteps.value[k] } as WorkflowRunStep;
            const key = parseInt(k);
            if (step) {
                if (isWorkflowInput(step.type) && !checkAndSetStepDescriptionForValidation(step)) {
                    let dataInput = inputs.value[step.id.toString()];
                    const formInput = formInputs.value.find((input) => parseInt(input.name) === step.id);
                    const optional = formInput?.optional as boolean;
                    const modelClass = formInput?.model_class as keyof typeof STEP_DESCRIPTIONS;

                    if (modelClass === "BooleanToolParameter") {
                        setStepDescription(step, dataInput as boolean, true);
                    } else if (modelClass === "DataToolParameter" || modelClass === "DataCollectionToolParameter") {
                        dataInput = dataInput as DataToolParameterInput | DataCollectionToolParameterInput;
                        const inputVals = dataInput?.values;
                        const options = formInput?.options;

                        if (inputVals?.length === 1 && inputVals[0]) {
                            const { id, src } = inputVals[0];
                            const item = options[src].find((option: any) => option.id === id);

                            if (item && item.hid && item.name) {
                                setStepDescription(step, `${item.hid}: <b>${item.name}</b>`, true);
                            }
                        } else if (inputVals?.length) {
                            setStepDescription(step, `${inputVals.length} inputs provided`, true);
                        } else {
                            setStepDescription(step, STEP_DESCRIPTIONS[modelClass], false, optional);
                        }
                    } else if (Object.keys(STEP_DESCRIPTIONS).includes(modelClass)) {
                        if (!dataInput || dataInput.toString().trim() === "") {
                            setStepDescription(step, STEP_DESCRIPTIONS[modelClass], false, optional);
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
                            setStepDescription(step, text, true);
                        }
                    } else {
                        set(step, "nodeText", "This is an input");
                    }
                }

                acc[key] = step;
            }
            return acc;
        }, {});
    });

    /** Annotate the step for the workflow graph with the current input value or prompt
     * @param step The step to annotate
     * @param text The text to display
     * @param populated Whether the input is populated, undefined for optional inputs
     * @param optional Whether the input is optional
     */
    function setStepDescription(step: WorkflowRunStep, text: string | boolean, populated: boolean, optional?: boolean) {
        // color variant for `paused` state works best for unpopulated inputs,
        // "" for optional inputs and `ok` for populated inputs
        const headerClass = optional ? "" : populated ? "ok" : "paused";
        const headerIcon = populated ? faCheckCircle : faExclamationCircle;

        text = typeof text === "boolean" ? text : !optional ? text : `${text} (optional)`;

        set(step, "nodeText", text);
        set(step, "headerClass", getHeaderClass(headerClass));
        set(step, "headerIcon", headerIcon);
    }

    function checkAndSetStepDescriptionForValidation(step: WorkflowRunStep): boolean {
        if (stepValidation.value && stepValidation.value.length == 2) {
            const [stepId, message] = stepValidation.value;

            if (stepId === step.id.toString()) {
                const text = message.length < 20 ? message : "Fix error(s) for this step";
                setStepDescription(step, text, false);
                return true;
            }
        }
        return false;
    }

    return {
        /** The steps of the workflow run graph */
        steps,
        /** Fetches the original workflow structure (once) and syncs the step
         * descriptions given the current user inputs.
         */
        loadWorkflowRunGraph,
        loading,
    };
}
