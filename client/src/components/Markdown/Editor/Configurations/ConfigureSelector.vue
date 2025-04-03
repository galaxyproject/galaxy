<template>
    <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
    <LoadingSpan v-else-if="!currentHistoryId" />
    <div
        v-else
        class="mb-2"
        :class="droppable && dragState && `ui-dragover-${dragState}`"
        @dragenter.prevent="onDragEnter"
        @dragleave.prevent="onDragLeave"
        @dragover.prevent
        @drop.prevent="onDrop">
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
import { type EventData, useEventStore } from "@/stores/eventStore";
import { useHistoryStore } from "@/stores/historyStore";

import { getRequiredLabels } from "@/components/Markdown/Utilities/requirements";

import LoadingSpan from "@/components/LoadingSpan.vue";

const eventStore = useEventStore();

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
const dragData: Ref<EventData[]> = ref([]);
const dragTarget: Ref<EventTarget | null> = ref(null);
const dragState: Ref<"success" | "warning" | null> = ref(null);
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

const droppable = computed(
    () => !hasLabels.value && ["history_dataset_id", "history_collection_dataset_id"].includes(props.objectType)
);

const hasLabels = computed(() => props.labels !== undefined);

const mappedLabels = computed(() =>
    props.labels
        ?.filter((workflowLabel) => getRequiredLabels(props.objectType).includes(workflowLabel.type))
        .map((workflowLabel) => ({
            name: `${workflowLabel.label} (${workflowLabel.type})`,
            label: {
                invocation_id: "",
                [workflowLabel.type]: workflowLabel.label,
            },
        }))
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
                options.value = data.map((d: any) => ({ id: d.id, name: d.name ?? d.id, label: d.label }));
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

function onDragEnter(evt: DragEvent) {
    dragState.value = "warning";
    dragTarget.value = evt.target;
    const eventData = eventStore.getDragItems();
    if (eventData?.length) {
        dragTarget.value = evt.target;
        dragData.value = eventData;
        dragState.value = "success";
    }
}

function onDragLeave(evt: DragEvent) {
    if (dragTarget.value === evt.target) {
        dragState.value = null;
    }
}

function onDrop() {
    if (droppable.value && dragData.value.length > 0) {
        const item = dragData.value[0];
        if (item) {
            const { id, name, history_content_type } = item;
            if (id && name) {
                const isDataset = props.objectType === "history_dataset_id" && history_content_type === "dataset";
                const isCollection =
                    props.objectType === "history_dataset_collection_id" &&
                    history_content_type === "dataset_collection";
                if (isDataset || isCollection) {
                    emit("change", { id, name } as OptionType);
                }
            }
        }
    }
    dragState.value = null;
}

watch(
    () => [props.objectType, currentHistoryId.value],
    () => search(),
    { immediate: true }
);
</script>
