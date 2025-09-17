<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { fetchPlugin, fetchPluginHistoryItems, type Plugin } from "@/api/plugins";
import type { OptionType } from "@/components/SelectionField/types";
import { useMarkdown } from "@/composables/markdown";
import { useHistoryStore } from "@/stores/historyStore";

import { getRequiresDataset, getTestExtensions, getTestUrls } from "./utilities";

import VisualizationExamples from "./VisualizationExamples.vue";
import Heading from "@/components/Common/Heading.vue";
import FormDataExtensions from "@/components/Form/Elements/FormData/FormDataExtensions.vue";
import FormCardSticky from "@/components/Form/FormCardSticky.vue";
import SelectionField from "@/components/SelectionField/SelectionField.vue";

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true, increaseHeadingLevelBy: 2 });

const { currentHistoryId } = storeToRefs(useHistoryStore());

const router = useRouter();

const props = defineProps<{
    visualization: string;
}>();

const errorMessage = ref("");
const formatsVisible = ref(false);
const plugin: Ref<Plugin | undefined> = ref();

const extensions = computed(() => getTestExtensions(plugin.value));
const requiresDataset = computed(() => getRequiresDataset(plugin.value));
const testUrls = computed(() => getTestUrls(plugin.value));

async function doQuery() {
    if (currentHistoryId.value && plugin.value) {
        const data = await fetchPluginHistoryItems(plugin.value.name, currentHistoryId.value);
        return [
            ...(!requiresDataset.value ? [{ id: "", name: "Create a new visualization..." }] : []),
            ...data.hdas.map((hda) => ({ id: hda.id, name: `${hda.hid}: ${hda.name}` })),
        ];
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

defineExpose({ doQuery });
</script>

<template>
    <FormCardSticky
        v-if="plugin"
        :error-message="errorMessage"
        :description="plugin.description"
        :is-loading="!currentHistoryId || !plugin"
        :logo="plugin?.logo"
        :name="plugin?.html">
        <template v-slot:buttons>
            <VisualizationExamples :url-data="testUrls" />
        </template>
        <div class="my-3">
            <SelectionField
                object-name="Make a selection..."
                object-title="Select to Visualize"
                object-type="history_dataset_id"
                :object-query="doQuery"
                @change="onSelect" />
            <FormDataExtensions
                v-if="extensions && extensions.length > 0"
                :extensions="extensions"
                formats-button-id="vis-create-ext"
                :formats-visible.sync="formatsVisible" />
        </div>
        <div v-if="plugin.help" class="my-2">
            <Heading h2 separator bold size="sm">Help</Heading>
            <div v-html="renderMarkdown(plugin.help)" />
        </div>
        <div class="my-2 pb-2">
            <div v-for="(tag, index) in plugin?.tags" :key="index" class="badge badge-info text-capitalize mr-1">
                {{ tag }}
            </div>
        </div>
    </FormCardSticky>
</template>
