<script setup lang="ts">
import { faEye } from "@fortawesome/free-solid-svg-icons";
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { fetchPlugin, fetchPluginHistoryItems, type Plugin } from "@/api/plugins";
import type { OptionType } from "@/components/SelectionField/types";
import { useHistoryStore } from "@/stores/historyStore";
import { absPath } from "@/utils/redirect";

import FormCard from "../Form/FormCard.vue";
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


        <div class="position-relative">
        <div class="ui-form-header-underlay sticky-top" />
        <div class="tool-header sticky-top bg-secondary px-2 py-1 rounded">
            <div class="d-flex justify-content-between">
                <div class="py-1 d-flex flex-wrap flex-gapx-1">
                    <span>
                        <img v-if="plugin.logo" class="fa-fw" alt="visualization" :src="absPath(plugin.logo)" />
                        <icon v-else :icon="faEye" class="fa-fw"  />
                        <Heading h1 inline bold size="text" itemprop="name">{{ plugin.html }}</Heading>
                    </span>
                    <span itemprop="description">{{ plugin.description }}</span>
                </div>
                <div class="d-flex flex-nowrap align-items-start flex-gapx-1">
                    <b-button-group class="tool-card-buttons">
                    </b-button-group>
                    <slot name="header-buttons" />
                </div>
            </div>
        </div>

        <div id="tool-card-body">
            <div v-for="(tag, index) in plugin.tags" :key="index" class="badge badge-info text-capitalize mr-1">
                {{ tag }}
            </div>
            <SelectionField
                class="my-3"
                object-name="Select a dataset..."
                object-title="Select to Visualize"
                object-type="history_dataset_id"
                :object-query="doQuery"
                @change="onSelect" />
        </div>

        <slot name="buttons" />

        <div>
            <div v-if="plugin.help" class="mt-2 mb-4">
                <Heading h2 separator bold size="sm"> Help </Heading>
                <MarkdownDefault :content="plugin.help" />
            </div>
        </div>
        </div>
    </div>
</template>
