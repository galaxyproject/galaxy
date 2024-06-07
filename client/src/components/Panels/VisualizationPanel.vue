<script setup lang="ts">
import { faEye } from "@fortawesome/free-solid-svg-icons";
import { BAlert, BModal } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

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

interface Dataset {
    id: string;
    name: string;
}

interface CompatibleDatasetsResponse {
    hdas: Dataset[];
}

const { currentHistoryId } = storeToRefs(useHistoryStore());
const router = useRouter();

const plugins: Ref<Array<Plugin>> = ref([]);
const query = ref("");
const isLoading = ref(true);
const currentPlugin: Ref<Plugin | null> = ref(null);
const compatibleDatasetIdKeys = ref<string[]>([]);
const showDataDialog = ref(false);
const showNoCompatibleDatasetsModal = ref(false);

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
        router.push(`/visualizations/display?visualization=${currentPlugin.value.name}&dataset_id=${dataset.id}`, {
            // @ts-ignore
            title: dataset.name,
        });
    }
}

async function selectVisualization(plugin: Plugin) {
    currentPlugin.value = plugin;
    compatibleDatasetIdKeys.value = await getCompatibleDatasetsInCurrentHistory();
    if (compatibleDatasetIdKeys.value.length === 0) {
        showNoCompatibleDatasetsModal.value = true;
        return;
    }
    showDataDialog.value = true;
}

/**
 * Get compatible datasets in the current history for the selected visualization.
 * @returns {Promise<string[]>} List of compatible datasets as "type-id" strings. In this case, type will be always "dataset".
 */
async function getCompatibleDatasetsInCurrentHistory(): Promise<string[]> {
    if (!currentPlugin.value || !currentHistoryId.value) {
        return [];
    }
    const result = (await urlData({
        url: `/api/plugins/${currentPlugin.value.name}`,
        params: { history_id: currentHistoryId.value },
    })) as CompatibleDatasetsResponse;
    return result.hdas.map((dataset: Dataset) => `dataset-${dataset.id}`);
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
        <template v-slot:header>
            <h3>Create Visualization</h3>
            <DelayedInput :delay="100" placeholder="Search visualizations" @change="query = $event" />
        </template>
        <div class="overflow-y mt-2">
            <LoadingSpan v-if="isLoading" message="Loading visualizations" />
            <div v-else-if="filteredPlugins.length > 0">
                <div v-for="plugin in filteredPlugins" :key="plugin.name">
                    <button :data-plugin-name="plugin.name" @click="selectVisualization(plugin)">
                        <div class="d-flex">
                            <div class="plugin-thumbnail mr-2">
                                <img v-if="plugin.logo" alt="visualization" :src="absPath(plugin.logo)" />
                                <icon v-else :icon="faEye" class="plugin-icon" />
                            </div>
                            <div class="text-break">
                                <div class="plugin-list-title font-weight-bold">{{ plugin.html }}</div>
                                <div class="plugin-list-text text-muted">{{ plugin.description }}</div>
                            </div>
                        </div>
                    </button>
                </div>
            </div>
            <BAlert v-else v-localize variant="info" show> No matching visualization found. </BAlert>
        </div>
        <DataDialog
            v-if="currentHistoryId && showDataDialog"
            format=""
            :history="currentHistoryId"
            :filter-ok-state="true"
            :filter-by-type-ids="compatibleDatasetIdKeys"
            @onOk="createVisualization"
            @onCancel="showDataDialog = false" />
        <BModal v-model="showNoCompatibleDatasetsModal" title="No compatible datasets found" title-tag="h2" ok-only>
            <p v-localize>
                No datasets found in your current history that are compatible with
                <b>{{ currentPlugin?.name ?? "this visualization" }}</b
                >. Please upload a compatible dataset or select a different visualization.
            </p>
        </BModal>
    </ActivityPanel>
</template>

<style lang="scss">
.plugin-thumbnail {
    img {
        width: 2rem;
    }
    .plugin-icon {
        font-size: 1.3rem;
        padding: 0.3rem;
    }
}
</style>
