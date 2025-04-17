<template>
    <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
    <BAlert v-else-if="!currentHistoryId || isLoading" variant="info" show>
        <LoadingSpan message="Please wait" />
    </BAlert>
    <BAlert v-else-if="options.length === 0" variant="info" show>
        No datasets found in your current history that are compatible. Please upload a compatible dataset.
    </BAlert>
    <div
        v-else
        :class="droppable && dragState && `ui-dragover-${dragState}`"
        role="presentation"
        aria-roledescription="drop zone"
        tabindex="0"
        @dragenter.prevent="onDragEnter"
        @dragleave.prevent="onDragLeave"
        @dragover.prevent
        @drop.prevent="onDrop">
        <label class="form-label font-weight-bold mb-2" for="multiselect">{{ title }}:</label>
        <Multiselect id="multiselect" v-model="currentValue" label="name" :options="options" @search-change="search" />
    </div>
</template>

<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { debounce } from "lodash";
import { storeToRefs } from "pinia";
import { computed, type Ref, ref, watch } from "vue";
import Multiselect from "vue-multiselect";

import {
    getDataset,
    getDatasetCollection,
    getHistories,
    getInvocations,
    getJobs,
    getWorkflows,
} from "@/components/SelectionField/services";
import { type EventData, useEventStore } from "@/stores/eventStore";
import { useHistoryStore } from "@/stores/historyStore";

import type { ApiResponse, OptionType } from "./types";

import LoadingSpan from "@/components/LoadingSpan.vue";

const eventStore = useEventStore();
const { currentHistoryId } = storeToRefs(useHistoryStore());

const DELAY = 300;

const props = withDefaults(
    defineProps<{
        objectId?: string;
        objectName?: string;
        objectQuery?: (query: string) => Promise<ApiResponse>;
        objectTitle?: string;
        objectType: string;
    }>(),
    {
        objectId: "",
        objectName: "...",
        objectQuery: undefined,
        objectTitle: undefined,
    }
);

const emit = defineEmits<{
    (e: "change", newValue: OptionType): void;
}>();

const errorMessage = ref("");
const dragData: Ref<EventData[]> = ref([]);
const dragTarget: Ref<EventTarget | null> = ref(null);
const dragState: Ref<"danger" | "success" | "warning" | null> = ref(null);
const isLoading = ref(true);
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

// Drag-and-drop only when labels are not used
const droppable = computed(() => ["history_dataset_id", "history_dataset_collection_id"].includes(props.objectType));

const title = computed(
    () =>
        props.objectTitle || `Select a ${props.objectType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}`
);

// Unified search behavior
const search = debounce(async (query: string = "") => {
    if (!errorMessage.value) {
        try {
            const data = await (props.objectQuery ? props.objectQuery(query) : doQuery(query));
            isLoading.value = false;
            errorMessage.value = "";
            if (data) {
                options.value = data.map((d: any) => ({ id: d.id, name: d.name ?? d.id, data: d }));
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
        case "history_dataset_collection_id":
            return getDatasetCollection(query, currentHistoryId.value);
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
        const item = eventData[0];
        if (item) {
            const { id, name, history_content_type } = item;
            if (id && name && isValidContent(history_content_type as string)) {
                dragTarget.value = evt.target;
                dragData.value = eventData;
                dragState.value = "success";
            } else {
                dragState.value = "danger";
            }
        }
    }
}

function onDragLeave(evt: DragEvent) {
    if (dragTarget.value === evt.target) {
        dragData.value = [];
        dragState.value = null;
    }
}

function onDrop() {
    if (droppable.value && dragData.value.length > 0) {
        const item = dragData.value[0];
        if (item) {
            const { id, name } = item;
            emit("change", { id, name } as OptionType);
        }
    }
    dragState.value = null;
}

function isValidContent(historyContentType: string) {
    const isDataset = props.objectType === "history_dataset_id" && historyContentType === "dataset";
    const isCollection =
        props.objectType === "history_dataset_collection_id" && historyContentType === "dataset_collection";
    return isDataset || isCollection;
}

watch(
    () => [props.objectType, currentHistoryId.value],
    () => search(),
    { immediate: true }
);
</script>
