<script setup lang="ts">
import { BAlert, BFormCheckbox } from "bootstrap-vue";
import { computed, ref } from "vue";

import { extractWorkflowFromHistory, type WorkflowExtractionSummary } from "@/api/histories";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import type { TableField } from "../Common/GTable.types";

import BreadcrumbHeading from "../Common/BreadcrumbHeading.vue";
import GTable from "../Common/GTable.vue";
import LoadingSpan from "../LoadingSpan.vue";
import WorkflowExtractionNode from "./WorkflowExtractionNode.vue";
import GenericHistoryItem from "@/components/History/Content/GenericItem.vue";

const props = defineProps<{
    historyId: string;
}>();

const historyStore = useHistoryStore();
const historyName = computed(() => historyStore.getHistoryNameById(props.historyId));

const breadcrumbItems = computed(() => [
    { title: "Histories", to: "/histories/list" },
    {
        title: historyName.value,
        to: `/histories/view?id=${props.historyId}`,
        superText: historyStore.currentHistoryId === props.historyId ? "current" : undefined,
    },
    { title: "Extract Workflow" },
]);

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const summary = ref<WorkflowExtractionSummary | null>(null);

const tableFields: TableField[] = [
    {
        key: "checked",
        label: "",
    },
    {
        key: "tool_name",
        label: "Workflow Step",
    },
    {
        key: "outputs",
        label: "Outputs",
        width: "25vw",
    },
];

extractWorkflow();

async function extractWorkflow() {
    try {
        summary.value = await extractWorkflowFromHistory(props.historyId);
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <BAlert v-else-if="loading" variant="info" show>
            <LoadingSpan message="Extracting workflow from history" />
        </BAlert>

        <div v-else-if="summary">
            <GTable :hover="false" :striped="false" :fields="tableFields" :items="summary.jobs">
                <template v-slot:cell(checked)="{ item }">
                    <BFormCheckbox v-model="item.checked" :disabled="Boolean(item.disabled_why)" @click.stop />
                </template>

                <template v-slot:cell(tool_name)="{ item }">
                    <WorkflowExtractionNode :job="item" />
                </template>

                <template v-slot:cell(outputs)="{ item }">
                    <div v-for="(output, index) in item.outputs" :key="index">
                        <GenericHistoryItem
                            :item-id="output.id"
                            :item-src="output.history_content_type === 'dataset' ? 'hda' : 'hdca'" />
                    </div>
                </template>
            </GTable>
        </div>

        <BAlert v-else variant="info" show> No workflow could be extracted from this history. </BAlert>
    </div>
</template>
