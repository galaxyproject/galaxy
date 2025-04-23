<script setup lang="ts">
import { storeToRefs } from "pinia";
import { onMounted, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { fetchPlugin, fetchPluginHistoryItems, type Plugin } from "@/api/plugins";
import type { OptionType } from "@/components/SelectionField/types";
import { useHistoryStore } from "@/stores/historyStore";

import VisualizationDropdown from "./VisualizationDropdown.vue";
import Heading from "@/components/Common/Heading.vue";
import FormCardSticky from "@/components/Form/FormCardSticky.vue";
//import JobRunner from "@/components/JobRunner/JobRunner.vue";
import MarkdownDefault from "@/components/Markdown/Sections/MarkdownDefault.vue";
import SelectionField from "@/components/SelectionField/SelectionField.vue";

const { currentHistoryId } = storeToRefs(useHistoryStore());

const router = useRouter();

const props = defineProps<{
    visualization: string;
}>();

const errorMessage = ref("");
const plugin: Ref<Plugin | undefined> = ref();

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
    <FormCardSticky
        :error-message="errorMessage"
        :description="plugin?.description"
        :is-loading="!currentHistoryId || !plugin"
        :logo="plugin?.logo"
        :name="plugin?.html">
        <template v-slot:buttons>
            <VisualizationDropdown :plugin="plugin" />
        </template>
        <SelectionField
            class="my-3"
            object-name="Select a dataset..."
            object-title="Select to Visualize"
            object-type="history_dataset_id"
            :object-query="doQuery"
            @change="onSelect" />
        <div v-if="plugin?.help" class="mt-2 mb-4">
            <Heading h2 separator bold size="sm">Help</Heading>
            <MarkdownDefault :content="plugin.help" />
        </div>
    </FormCardSticky>
</template>
