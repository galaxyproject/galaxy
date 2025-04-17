<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { onMounted, ref } from "vue";

import { fetchPlugin, fetchPluginHistoryItems } from "@/api/plugins";
import { useHistoryStore } from "@/stores/historyStore";

import VisualizationHeader from "./VisualizationHeader.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import SelectionField from "@/components/SelectionField/SelectionField.vue";

import type { OptionType } from "@/components/SelectionField/types";

const { currentHistoryId } = storeToRefs(useHistoryStore());

const props = defineProps<{
    visualization: string;
}>();

const errorMessage = ref("");
const isLoading = ref(true);
const plugin = ref();

async function doQuery() {
    if (currentHistoryId.value) {
        const data = await fetchPluginHistoryItems(plugin.value.name, currentHistoryId.value);
        return data.hdas;
    } else {
        return [];
    }
}

async function getPlugin() {
    plugin.value = await fetchPlugin(props.visualization);
    isLoading.value = false;
}

function onSelect(value: OptionType) {
    console.log(value);
}

onMounted(() => {
    getPlugin();
});
</script>

<template>
    <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
    <LoadingSpan v-else-if="!currentHistoryId || isLoading" message="Loading visualization" />
    <div v-else>
        <VisualizationHeader :plugin="plugin" class="mb-2" />
        <SelectionField object-title="Dataset" object-type="history_dataset_id" :object-query="doQuery" @change="onSelect"/>
    </div>
</template>
