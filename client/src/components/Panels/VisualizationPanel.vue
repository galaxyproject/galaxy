<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, onMounted, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { fetchPlugins, type Plugin } from "@/api/plugins";

import ButtonPlain from "@/components/Common/ButtonPlain.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
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
        if (plugin.ext) {
            content += plugin.ext.join();
        }
        if (plugin.help) {
            content += plugin.help;
        }
        if (plugin.tags) {
            content += plugin.tags.join();
        }
        result[plugin.name] = content.toLowerCase();
    });
    return result;
});

const filteredPlugins = computed(() => {
    const queryLower = query.value.trim().toLowerCase();
    if (!queryLower) {
        return plugins.value;
    }
    return plugins.value.filter((plugin) => {
        return queryIndex.value[plugin.name]?.includes(queryLower);
    });
});

async function selectVisualization(plugin: Plugin) {
    if (props.datasetId) {
        router.push(`/visualizations/display?visualization=${plugin.name}&dataset_id=${props.datasetId}`);
    } else {
        router.push(`/visualizations/create/${plugin.name}`);
    }
}

async function getPlugins() {
    plugins.value = await fetchPlugins(props.datasetId);
    isLoading.value = false;
}

onMounted(() => {
    getPlugins();
});
</script>

<template>
    <ActivityPanel title="Visualizations" go-to-all-title="Saved Visualizations" href="/visualizations/list">
        <template v-slot:header>
            <DelayedInput :delay="100" class="my-2" placeholder="search visualizations" @change="query = $event" />
        </template>
        <div>
            <LoadingSpan v-if="isLoading" message="Loading visualizations" />
            <div v-else-if="filteredPlugins.length > 0">
                <div v-for="plugin in filteredPlugins" :key="plugin.name">
                    <ButtonPlain
                        class="plugin-item rounded p-2"
                        :data-plugin-name="plugin.name"
                        @click="selectVisualization(plugin)">
                        <VisualizationHeader :plugin="plugin" />
                    </ButtonPlain>
                </div>
            </div>
            <BAlert v-else v-localize variant="info" show> No matching visualization found. </BAlert>
        </div>
    </ActivityPanel>
</template>

<style lang="scss">
@import "theme/blue.scss";

.plugin-item:hover {
    background: $gray-200;
}
</style>
