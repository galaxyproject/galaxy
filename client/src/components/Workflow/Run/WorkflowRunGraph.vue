<script setup lang="ts">
import { faCheckCircle, faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { BAlert, BCard } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { ref, set, watch } from "vue";

import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { getHeaderClass } from "@/composables/useInvocationGraph";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { isWorkflowInput } from "../constants";
import { fromSimple } from "../Editor/modules/model";

import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

interface BaseDataToolParameterInput {
    batch: boolean;
    product: boolean;
    values: { id: string; src: "dce" | "hda" | "hdca" | "ldda"; map_over_type: string }[];
}
interface DataToolParameterInput extends BaseDataToolParameterInput {}
interface DataCollectionToolParameterInput extends BaseDataToolParameterInput {}
type DataInput = DataToolParameterInput | DataCollectionToolParameterInput | boolean | string | null;

interface Props {
    workflowId: string;
    storedId: string;
    version: number;
    inputs: Record<string, DataInput | null>;
    stepValidation: any; // TODO: type as [string, string] | null;
    formInputs: any[];
}

const props = defineProps<Props>();

const hasLoadedGraph = ref(false);
const errorMessage = ref<string | null>(null);
const loadedWorkflow = ref<any | null>(null);

const { stateStore } = provideScopedWorkflowStores(props.workflowId);
const { activeNodeId } = storeToRefs(stateStore);

const datatypesMapperStore = useDatatypesMapperStore();
const { datatypesMapper, loading: datatypesMapperLoading } = storeToRefs(datatypesMapperStore);

watch(
    () => props.workflowId,
    async () => {
        try {
            loadedWorkflow.value = await getWorkflowFull(props.workflowId, props.version);

            syncStepsWithInputVals();

            await fromSimple(props.workflowId, loadedWorkflow.value);
        } catch (error) {
            errorMessage.value = errorMessageAsString(error);
        } finally {
            hasLoadedGraph.value = true;
        }
    },
    { immediate: true }
);

/** Sync the workflow graph steps with the current input values */
function syncStepsWithInputVals() {
    if (!loadedWorkflow.value?.steps) {
        return;
    }
    for (const s of Object.values(loadedWorkflow.value?.steps)) {
        const step = s as any;
        if (isWorkflowInput(step.type)) {
            let dataInput = props.inputs[step.id.toString()];
            const formInput = props.formInputs.find((input) => parseInt(input.name) === step.id);
            const optional = formInput?.optional as boolean;

            if (formInput.model_class === "BooleanToolParameter") {
                setStepDescription(step, dataInput as boolean, true);
            } else if (
                ["TextToolParameter", "IntegerToolParameter", "FloatToolParameter"].includes(formInput.model_class)
            ) {
                if (!dataInput || dataInput.toString().trim() === "") {
                    let infoText: string;
                    switch (formInput.model_class) {
                        case "TextToolParameter":
                            infoText = `Provide text input${optional ? " (optional)" : ""}`;
                            break;
                        case "IntegerToolParameter":
                            infoText = `Provide an integer${optional ? " (optional)" : ""}`;
                            break;
                        default:
                            infoText = `Provide a float${optional ? " (optional)" : ""}`;
                            break;
                    }
                    setStepDescription(step, infoText, false, optional);
                } else {
                    setStepDescription(step, `<b>${dataInput}</b>`, true);
                }
            } else if (formInput.model_class === "ColorToolParameter") {
                if (!dataInput) {
                    setStepDescription(step, "Provide a color", false);
                } else {
                    setStepDescription(step, dataInput as string, true);
                }
            } else if (formInput.model_class === "DirectoryUriToolParameter") {
                if (!dataInput) {
                    setStepDescription(step, `Provide a directory${optional ? " (optional)" : ""}`, false, optional);
                } else {
                    setStepDescription(step, `Directory: <b>${dataInput}</b>`, true);
                }
            } else if (
                formInput.model_class === "DataToolParameter" ||
                formInput.model_class === "DataCollectionToolParameter"
            ) {
                dataInput = dataInput as DataToolParameterInput | DataCollectionToolParameterInput;
                const inputVals = dataInput?.values;
                const options = formInput?.options;

                if (inputVals?.length === 1 && inputVals[0]) {
                    const { id, src } = inputVals[0];
                    const item = options[src].find((option: any) => option.id === id);
                    setStepDescription(step, `${item.hid}: <b>${item.name}</b>`, true);
                } else if (inputVals?.length) {
                    setStepDescription(step, `${inputVals.length} inputs provided`, true);
                } else if (formInput.model_class === "DataToolParameter") {
                    setStepDescription(step, `Provide a dataset${optional ? " (optional)" : ""}`, false, optional);
                } else {
                    setStepDescription(step, `Provide a collection${optional ? " (optional)" : ""}`, false, optional);
                }
            } else {
                set(step, "nodeText", "This is an input");
            }
        }
    }
}

/** Annotate the step for the workflow graph with the current input value or prompt
 * @param step The step to annotate
 * @param text The text to display
 * @param populated Whether the input is populated, undefined for optional inputs
 * @param optional Whether the input is optional
 */
function setStepDescription(step: any, text: string | boolean, populated: boolean, optional?: boolean) {
    // color variant for `paused` state works best for unpopulated inputs,
    // "" for optional inputs and `ok` for populated inputs
    const headerClass = optional ? "" : populated ? "ok" : "paused";
    const headerIcon = populated ? faCheckCircle : faExclamationCircle;

    set(step, "nodeText", text);
    set(step, "headerClass", getHeaderClass(headerClass));
    set(step, "headerIcon", headerIcon);
}

function setStepDescriptionForValidation(): boolean {
    if (props.stepValidation && props.stepValidation.length == 2) {
        const [stepId, message] = props.stepValidation;
        const step = loadedWorkflow.value.steps[stepId];
        if (step) {
            const text = message.length < 20 ? message : "Fix error(s) for this step";
            setStepDescription(step, text, false);
            return true;
        }
    }
    return false;
}

watch(
    () => props.inputs,
    () => {
        syncStepsWithInputVals();
    }
);

watch(
    () => props.stepValidation,
    () => {
        if (!loadedWorkflow.value?.steps) {
            return;
        }
        setStepDescriptionForValidation();
    },
    { immediate: true }
);
</script>

<template>
    <BAlert v-if="errorMessage" variant="danger" show>
        {{ errorMessage }}
    </BAlert>
    <BAlert v-else-if="datatypesMapperLoading || !loadedWorkflow" variant="info" show>
        <LoadingSpan message="Loading workflow" />
    </BAlert>
    <div v-else-if="datatypesMapper && hasLoadedGraph" class="d-flex flex-column">
        <Heading h2 separator bold size="sm"> Graph </Heading>
        <BCard class="workflow-preview mx-1 flex-grow-1">
            <WorkflowGraph
                v-if="loadedWorkflow.steps"
                :steps="loadedWorkflow.steps"
                :datatypes-mapper="datatypesMapper"
                :scroll-to-id="activeNodeId"
                populated-inputs
                show-minimap
                show-zoom-controls
                readonly />
        </BCard>
    </div>
</template>

<style scoped>
.alert {
    width: 100%;
    margin: 2rem;
    text-align: center;
    align-content: center;
}
</style>
