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

interface Input {
    batch: boolean;
    product: boolean;
    values: { id: string; src: "dce" | "hda" | "hdca" | "ldda"; map_over_type: string }[];
}

interface Props {
    workflowId: string;
    storedId: string;
    version: number;
    inputs: Record<string, Input | null>;
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
            const dataInput = props.inputs[step.id.toString()];
            const inputVals = dataInput?.values;

            const formInput = props.formInputs.find((input) => parseInt(input.name) === step.id);
            const options = formInput?.options;

            if (inputVals?.length === 1 && inputVals[0]) {
                const { id, src } = inputVals[0];
                const item = options[src].find((option: any) => option.id === id);
                set(step, "nodeText", `${item.hid}: <b>${item.name}</b>`);
                set(step, "headerClass", getHeaderClass("ok"));
                set(step, "headerIcon", faCheckCircle);
            } else if (inputVals?.length) {
                set(step, "nodeText", `${inputVals.length} inputs provided`);
                set(step, "headerClass", getHeaderClass("ok"));
                set(step, "headerIcon", faCheckCircle);
            } else {
                set(step, "nodeText", "Populate this input");

                // color variant for `running` state works best
                set(step, "headerClass", getHeaderClass("running"));
                set(step, "headerIcon", faExclamationCircle);
            }
        }
    }
}

watch(
    () => props.inputs,
    () => {
        syncStepsWithInputVals();
    }
);
</script>

<template>
    <BAlert v-if="errorMessage" variant="danger" show>
        {{ errorMessage }}
    </BAlert>
    <BAlert v-else-if="datatypesMapperLoading || !loadedWorkflow" variant="info" show>
        <LoadingSpan message="Loading workflow" />
        {{ datatypesMapperLoading ? "mapperLoading" : "mapper loaded" }}
    </BAlert>
    <div v-else-if="datatypesMapper && hasLoadedGraph">
        <Heading h2 separator bold size="sm"> Graph </Heading>
        <BCard class="workflow-preview mx-1">
            <WorkflowGraph
                v-if="loadedWorkflow.steps"
                :steps="loadedWorkflow.steps"
                :datatypes-mapper="datatypesMapper"
                :scroll-to-id="activeNodeId"
                fixed-height
                populated-inputs
                show-minimap
                show-zoom-controls
                readonly />
        </BCard>
    </div>
</template>
