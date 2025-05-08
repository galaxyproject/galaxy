<script setup lang="ts">
import { BAlert, BCard } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { ref, toRef } from "vue";

import { type DataInput, useWorkflowRunGraph } from "@/composables/useWorkflowRunGraph";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { errorMessageAsString } from "@/utils/simple-error";

import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

interface Props {
    workflowId: string;
    storedId: string;
    version: number;
    inputs: Record<string, DataInput | null>;
    stepValidation?: [string, string];
    formInputs: any[];
}

const props = defineProps<Props>();

const errorMessage = ref<string | null>(null);

const { activeNodeId } = storeToRefs(useWorkflowStateStore(props.workflowId));

const datatypesMapperStore = useDatatypesMapperStore();
const { datatypesMapper, loading: datatypesMapperLoading } = storeToRefs(datatypesMapperStore);

const { steps, loading, loadWorkflowOntoGraph } = useWorkflowRunGraph(
    props.workflowId,
    props.version,
    toRef(props, "inputs"),
    toRef(props, "formInputs"),
    toRef(props, "stepValidation")
);

try {
    loadWorkflowOntoGraph();
} catch (error) {
    errorMessage.value = errorMessageAsString(error);
}
</script>

<template>
    <BAlert v-if="errorMessage" variant="danger" show>
        {{ errorMessage }}
    </BAlert>
    <BAlert v-else-if="datatypesMapperLoading || loading" variant="info" show>
        <LoadingSpan message="Loading workflow" />
    </BAlert>
    <div v-else-if="datatypesMapper && !loading" class="d-flex flex-column">
        <Heading h2 separator bold size="sm"> Graph </Heading>
        <BCard class="workflow-preview mx-1 flex-grow-1">
            <WorkflowGraph
                v-if="steps"
                :steps="steps"
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
