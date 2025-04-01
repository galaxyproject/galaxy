<template>
    <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
    <LoadingSpan v-else-if="!currentHistoryId" />
    <div v-else class="mb-2">
        <label class="form-label font-weight-bold">{{ title }}:</label>
        <Multiselect v-model="currentValue" label="name" :options="options" @search-change="search" />
    </div>
</template>

<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { debounce } from "lodash";
import { storeToRefs } from "pinia";
import { computed, type Ref, ref, watch } from "vue";
import Multiselect from "vue-multiselect";

import type { ApiResponse, OptionType, WorkflowLabel } from "@/components/Markdown/Editor/types";
import { getDataset, getHistories, getInvocations, getJobs, getWorkflows } from "@/components/Markdown/services";
import { useHistoryStore } from "@/stores/historyStore";

import LoadingSpan from "@/components/LoadingSpan.vue";

const { currentHistoryId } = storeToRefs(useHistoryStore());

const DELAY = 300;

const props = withDefaults(
    defineProps<{
        labels?: Array<WorkflowLabel>;
        objectId?: string;
        objectName?: string;
        objectTitle?: string;
        objectType: string;
    }>(),
    {
        objectId: "",
        objectName: "...",
    }
);

const emit = defineEmits<{
    (e: "change", newValue: OptionType): void;
}>();

const errorMessage = ref("");
const options: Ref<Array<OptionType>> = ref([]);

const currentValue = computed({
    get: () => ({
        id: props.objectId,
        name: props.objectName,
    }),
    set: (newValue: OptionType) => {
        emit("change", newValue);
    },
});

const availableLabels = computed(() => {
    switch (props.objectType) {
        case "history_dataset_id":
            return ["input", "output"];
        case "history_dataset_collection_id":
            return ["input", "output"];
        case "job_id":
            return ["step"];
    }
    return [];
});

const hasLabels = computed(() => props.labels !== undefined);

const mappedLabels = computed(() =>
    props.labels
        ?.filter((value) => availableLabels.value.includes(value.type))
        .map((value) => ({ name: `${value.label} (${value.type})`, value: value }))
);

const title = computed(
    () =>
        props.objectTitle || `Select a ${props.objectType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}`
);

const search = debounce(async (query: string = "") => {
    if (!errorMessage.value) {
        try {
            const data = hasLabels.value ? mappedLabels.value : await doQuery(query);
            errorMessage.value = "";
            if (data) {
                options.value = data.map((d: any) => ({ id: d.id, name: d.name ?? d.id, value: d.value }));
            } else {
                options.value = [];
            }
        } catch (e) {
            errorMessage.value = String(e);
        }
    }
}, DELAY);

async function doQuery(query: string = ""): Promise<ApiResponse> {
    switch (props.objectType) {
        case "history_id":
            return getHistories();
        case "history_dataset_id":
            return getDataset(query, currentHistoryId.value);
        case "invocation_id":
            return getInvocations();
        case "job_id":
            return getJobs();
        case "workflow_id":
            return getWorkflows();
    }
}

watch(
    () => [props.objectType, currentHistoryId.value],
    () => search(),
    { immediate: true }
);
</script>
