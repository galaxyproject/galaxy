<template>
    <b-alert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</b-alert>
    <div v-else>
        <label class="form-label font-weight-bold">Select a {{ objectTitle }}:</label>
        <Multiselect v-model="currentValue" label="name" :options="options" @search-change="search" />
    </div>
</template>

<script setup lang="ts">
import { debounce } from "lodash";
import { computed, type Ref, ref, watch } from "vue";
import Multiselect from "vue-multiselect";

import { getDataset, getHistories, getInvocations, getJobs, getWorkflows } from "@/components/Markdown/services";

import type { ApiResponse, OptionType } from "./types";

const DELAY = 300;

const props = defineProps<{
    objectType: string;
    objectId?: string;
}>();

const emit = defineEmits<{
    (e: "change", newValue: OptionType): void;
}>();

const errorMessage = ref("");
const objectName = ref("...");
const options: Ref<Array<OptionType>> = ref([]);

const currentValue = computed({
    get: () => ({
        id: props.objectId,
        name: objectName.value,
    }),
    set: (newValue: OptionType) => {
        emit("change", newValue);
    },
});

const objectTitle = computed(() => props.objectType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()));

const search = debounce(async (query: string = "") => {
    if (!errorMessage.value) {
        try {
            const data = await doQuery(query);
            errorMessage.value = "";
            if (data) {
                options.value = data.map((d: any) => ({ id: d.id, name: d.name ?? d.id }));
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
            return getDataset(query);
        case "invocation_id":
            return getInvocations();
        case "job_id":
            return getJobs();
        case "workflow_id":
            return getWorkflows();
    }
}

watch(
    () => props.objectType,
    () => search(),
    { immediate: true }
);
</script>
