<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { type Dataset, fetchPlugin, fetchPluginHistoryItems, type Plugin } from "@/api/plugins";
import type { OptionType } from "@/components/SelectionField/types";
import { useMarkdown } from "@/composables/markdown";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import { getTestExtensions, getTestUrls } from "./utilities";

import VisualizationExamples from "./VisualizationExamples.vue";
import Heading from "@/components/Common/Heading.vue";
import FormDataExtensions from "@/components/Form/Elements/FormData/FormDataExtensions.vue";
import FormCardSticky from "@/components/Form/FormCardSticky.vue";
import SelectionField from "@/components/SelectionField/SelectionField.vue";

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true, increaseHeadingLevelBy: 2 });

const { currentHistoryId } = storeToRefs(useHistoryStore());
const { isAnonymous } = storeToRefs(useUserStore());

const router = useRouter();

const props = defineProps<{
    visualization: string;
}>();

const errorMessage = ref("");
const plugin: Ref<Plugin | undefined> = ref();

const urlData = computed(() => getTestUrls(plugin.value));
const extensions = computed(() => getTestExtensions(plugin.value));
const formatsVisible = ref(false);

function addHidToName(hdas: Array<Dataset>) {
    return hdas.map((entry) => ({ id: entry.id, name: `${entry.hid}: ${entry.name}` }));
}

async function doQuery() {
    if (currentHistoryId.value && plugin.value) {
        const data = await fetchPluginHistoryItems(plugin.value.name, currentHistoryId.value);
        return addHidToName(data.hdas);
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
            <VisualizationExamples :url-data="urlData" />
        </template>
        <div class="my-3">
            <BAlert v-if="plugin.requires_login && isAnonymous" v-localize variant="warning" show>
                Please log in to access this visualization.
            </BAlert>
            <SelectionField
                v-else
                object-name="Select a dataset..."
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
            <div v-for="(tag, index) in plugin.tags" :key="index" class="badge badge-info text-capitalize mr-1">
                {{ tag }}
            </div>
        </div>
    </FormCardSticky>
</template>
