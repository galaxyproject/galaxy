<script setup lang="ts">
import { faEye } from "@fortawesome/free-solid-svg-icons";
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { fetchPlugin, fetchPluginHistoryItems, type Plugin } from "@/api/plugins";
import type { OptionType } from "@/components/SelectionField/types";
import { useHistoryStore } from "@/stores/historyStore";

import VisualizationHeader from "./VisualizationHeader.vue";
import Heading from "@/components/Common/Heading.vue";
import JobRunner from "@/components/JobRunner/JobRunner.vue";
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

const urlTuples = computed(
    () =>
        plugin.value?.tests
            ?.map((item) => {
                const url = item.param?.name === "dataset_id" ? item.param?.value : null;
                if (url) {
                    const filename = getFilename(url);
                    return filename.trim() ? ([filename, url] as [string, string]) : null;
                }
            })
            .filter((tuple): tuple is [string, string] => Boolean(tuple)) ?? []
);

async function doQuery() {
    if (currentHistoryId.value && plugin.value) {
        const data = await fetchPluginHistoryItems(plugin.value.name, currentHistoryId.value);
        return data.hdas;
    } else {
        return [];
    }
}

function getFilename(url: string): string {
    try {
        const pathname = new URL(url).pathname;
        const parts = pathname.split("/").filter(Boolean);
        return parts.length ? parts.pop()! : "";
    } catch {
        return "";
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
        <div v-if="urlTuples && urlTuples.length > 0">
            <Heading separator size="sm">Sample Datasets</Heading>
            <div class="d-flex flex-wrap">
                <JobRunner
                    v-for="([url, name], index) in urlTuples"
                    :key="index"
                    class="m-1"
                    :icon="faEye"
                    :title="url"
                    :payload="{ url: name }"
                    @ok="onSelect" />
            </div>
        </div>
    </div>
</template>
