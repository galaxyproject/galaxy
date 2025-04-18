<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { fetchPlugin, fetchPluginHistoryItems, type Plugin } from "@/api/plugins";
import type { OptionType } from "@/components/SelectionField/types";
import { useHistoryStore } from "@/stores/historyStore";

import VisualizationHeader from "./VisualizationHeader.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import MarkdownDefault from "@/components/Markdown/Sections/MarkdownDefault.vue";
import SelectionField from "@/components/SelectionField/SelectionField.vue";

const { currentHistoryId } = storeToRefs(useHistoryStore());

const router = useRouter();

const props = defineProps<{
    visualization: string;
}>();

const errorMessage = ref("");
const plugin: Ref<Plugin | undefined> = ref();

const samples = computed(() =>
    plugin.value?.tests?.filter((item) => item.param?.name === "dataset_id").map((item) => item.param.value)
);

async function doQuery() {
    if (currentHistoryId.value && plugin.value) {
        const data = await fetchPluginHistoryItems(plugin.value.name, currentHistoryId.value);
        return data.hdas;
    } else {
        return [];
    }
}

async function getPlugin() {
    plugin.value = await fetchPlugin(props.visualization);
}

function onSelect(dataset: OptionType) {
    router.push(`/visualizations/display?visualization=${plugin.value?.name}&dataset_id=${dataset.id}`, {
        // @ts-ignore
        title: dataset.name,
    });
}

onMounted(() => {
    getPlugin();
});
</script>

<template>
    <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
    <LoadingSpan v-else-if="!currentHistoryId || !plugin" message="Loading visualization" />
    <div v-else>
        <VisualizationHeader :plugin="plugin" />
        <SelectionField
            class="my-3"
            object-name="Select a dataset..."
            object-title="Select to Visualize"
            object-type="history_dataset_id"
            :object-query="doQuery"
            @change="onSelect" />
        <MarkdownDefault v-if="plugin.help" :content="plugin.help" />
        <div v-for="(sample, sampleIndex) in samples" :key="sampleIndex">
            {{ sample }}
        </div>
    </div>
</template>
