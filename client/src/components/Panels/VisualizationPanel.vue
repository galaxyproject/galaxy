<script setup lang="ts">
import { faEye } from "@fortawesome/free-solid-svg-icons";
import { storeToRefs } from "pinia";
import { computed, onMounted, type Ref, ref } from "vue";

import { useHistoryStore } from "@/stores/historyStore";
import { absPath } from "@/utils/redirect";
import { urlData } from "@/utils/url";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import DataDialog from "@/components/DataDialog/DataDialog.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

interface Plugin {
    description: string;
    href: string;
    html: string;
    logo?: string;
    name: string;
    target?: string;
}

const { currentHistoryId } = storeToRefs(useHistoryStore());

const plugins: Ref<Array<Plugin>> = ref([]);
const query = ref("");
const isLoading = ref(true);
const currentPlugin: Ref<Plugin | null> = ref(null);
const showDataDialog = ref(false);

const filteredPlugins = computed(() => {
    const queryLower = query.value.toLowerCase();
    return plugins.value.filter(
        (plugin) =>
            !query.value ||
            plugin.html.toLowerCase().includes(queryLower) ||
            (plugin.description && plugin.description.toLowerCase().includes(queryLower))
    );
});

function createVisualization(dataset: any) {
    showDataDialog.value = false;
    if (currentPlugin.value) {
        const href = `${currentPlugin.value.href}?dataset_id=${dataset.id}`;
        if (currentPlugin.value.target == "_top") {
            window.location.href = href;
        } else {
            const galaxyMainElement = document.getElementById("galaxy_main");
            if (galaxyMainElement) {
                galaxyMainElement.setAttribute("src", href);
            }
        }
    }
}

function selectVisualization(plugin: Plugin) {
    currentPlugin.value = plugin;
    showDataDialog.value = true;
}

async function getPlugins() {
    plugins.value = await urlData({ url: "/api/plugins" });
    isLoading.value = false;
}

onMounted(() => {
    getPlugins();
});
</script>

<template>
    <ActivityPanel title="Visualizations" go-to-all-title="Saved Visualizations" href="/visualizations/list">
        <h3>Create Visualization</h3>
        <DelayedInput :delay="100" placeholder="Search visualizations" @change="query = $event" />
        <div class="overflow-y mt-2">
            <LoadingSpan v-if="isLoading" message="Loading visualizations" />
            <div v-else-if="filteredPlugins.length > 0">
                <div v-for="plugin in filteredPlugins" :key="plugin.name">
                    <button :data-plugin-name="plugin.name" @click="selectVisualization(plugin)">
                        <div class="d-flex">
                            <div class="plugin-thumbnail mr-3">
                                <img v-if="plugin.logo" alt="visualization" :src="absPath(plugin.logo)" />
                                <icon v-else :icon="faEye" class="plugin-icon" />
                            </div>
                            <div class="text-break">
                                <div class="plugin-list-title font-weight-bold">{{ plugin.html }}</div>
                                <div class="plugin-list-text">{{ plugin.description }}</div>
                            </div>
                        </div>
                    </button>
                </div>
            </div>
            <BAlert v-else v-localize variant="info" show> No matching visualization found. </BAlert>
        </div>
        <DataDialog
            v-if="showDataDialog"
            format=""
            :history="currentHistoryId"
            @onOk="createVisualization"
            @onCancel="showDataDialog = false" />
    </ActivityPanel>
</template>

<style lang="scss">
.plugin-thumbnail {
    img {
        width: 2rem;
    }
    .plugin-icon {
        font-size: 1.5rem;
        padding: 0.2rem;
    }
}
</style>
