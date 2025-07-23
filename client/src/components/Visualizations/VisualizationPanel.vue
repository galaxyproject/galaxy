<script setup lang="ts">
import { computed, onMounted, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { fetchPlugins, type Plugin } from "@/api/plugins";

import { getTestExtensions } from "./utilities";

import ScrollList from "@/components/ScrollList/ScrollList.vue";
import ButtonPlain from "@/components/Common/ButtonPlain.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import VisualizationHeader from "@/components/Visualizations/VisualizationHeader.vue";

const router = useRouter();

const props = defineProps<{
    datasetId?: string;
}>();

const plugins: Ref<Plugin[]> = ref([]);
const query = ref("");
const isLoading = ref(true);

const queryIndex = computed(() => {
    const result: Record<string, string> = {};
    plugins.value.forEach((plugin) => {
        let content = plugin.html;
        if (plugin.description) {
            content += plugin.description;
        }
        const extensions = getTestExtensions(plugin);
        if (extensions) {
            content += extensions.join();
        }
        if (plugin.help) {
            content += plugin.help;
        }
        if (plugin.tags) {
            content += plugin.tags.join();
        }
        result[plugin.name] = normalize(content);
    });
    return result;
});

const filteredPlugins = computed(() => {
    const rawTokens = query.value.trim().split(/\s+/).filter(Boolean);
    if (rawTokens.length === 0) {
        return plugins.value;
    }
    const tokens = rawTokens.map(normalize);
    return plugins.value.filter((plugin) => {
        const index = queryIndex.value[plugin.name];
        return tokens.every((token) => index?.includes(token));
    });
});

async function selectVisualization(plugin: Plugin) {
    if (props.datasetId) {
        router.push(`/visualizations/display?visualization=${plugin.name}&dataset_id=${props.datasetId}`, {
            // @ts-ignore
            title: plugin.name,
        });
    } else {
        router.push(`/visualizations/create/${plugin.name}`);
    }
}

async function getPlugins() {
    plugins.value = await fetchPlugins(props.datasetId);
    plugins.value.sort((a, b) => {
        if (b.embeddable === true && a.embeddable !== true) {
            return 1;
        }
        if (a.embeddable === true && b.embeddable !== true) {
            return -1;
        }
        return a.html.localeCompare(b.html);
    });
    isLoading.value = false;
}

function normalize(text: string): string {
    return text.toLowerCase().replace(/[^a-z0-9]/gi, "");
}

onMounted(() => {
    getPlugins();
});
</script>

<template>
    <ActivityPanel
        title="Visualizations"
        :go-to-all-title="datasetId ? undefined : 'Saved Visualizations'"
        href="/visualizations/list">
        <template v-slot:header>
            <DelayedInput :delay="100" class="my-2" placeholder="search visualizations" @change="query = $event" />
        </template>
        <ScrollList
            :item-key="(plugin) => plugin.name"
            in-panel
            name="visualization"
            name-plural="visualizations"
            load-disabled
            :prop-items="filteredPlugins"
            :prop-total-count="plugins.length"
            :prop-busy="isLoading">
            <template v-slot:item="{ item: plugin }">
                <ButtonPlain
                    class="plugin-item rounded p-2"
                    :data-plugin-name="plugin.name"
                    @click="selectVisualization(plugin)">
                    <VisualizationHeader :plugin="plugin" />
                </ButtonPlain>
            </template>
        </ScrollList>
    </ActivityPanel>
</template>

<style lang="scss">
@import "theme/blue.scss";

.plugin-item:hover {
    background: $gray-200;
}
</style>
