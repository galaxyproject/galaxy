<template>
    <div aria-labelledby="visualizations-admin-heading">
        <Heading id="visualizations-admin-heading" h1 size="lg">Visualizations Management</Heading>

        <b-tabs v-model="activeTabIndex" class="mb-3">
            <b-tab>
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faList" class="mr-1" />
                    Installed ({{ installedVisualizations.length }})
                </template>
            </b-tab>
            <b-tab>
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faDownload" class="mr-1" />
                    Available
                </template>
            </b-tab>
            <b-tab>
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faChartBar" class="mr-1" />
                    Usage Stats
                </template>
            </b-tab>
            <b-tab>
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faServer" class="mr-1" />
                    Staging
                </template>
            </b-tab>
        </b-tabs>

        <b-button
            v-if="activeTab === 'installed'"
            variant="outline-secondary"
            class="mb-3"
            :disabled="loading"
            @click="reloadRegistry">
            <FontAwesomeIcon :icon="faSync" :spin="loading" class="mr-1" />
            Reload Registry
        </b-button>

        <!-- Installed Visualizations Tab -->
        <div v-if="activeTab === 'installed'">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div>
                    <b-form-checkbox v-model="showDisabled" class="mr-3">
                        Show disabled visualizations
                    </b-form-checkbox>
                </div>
                <div>
                    <b-input-group>
                        <b-form-input
                            v-model="searchFilter"
                            placeholder="Filter visualizations..."
                            @input="filterInstalled" />
                        <b-input-group-append>
                            <b-button
                                variant="outline-secondary"
                                @click="
                                    searchFilter = '';
                                    filterInstalled();
                                ">
                                <FontAwesomeIcon :icon="faTimes" />
                            </b-button>
                        </b-input-group-append>
                    </b-input-group>
                </div>
            </div>

            <div v-if="loading" class="text-center py-4">
                <b-spinner label="Loading..." />
                <p class="mt-2">Loading visualization packages...</p>
            </div>

            <div v-else-if="filteredInstalledVisualizations.length === 0" class="text-center py-4">
                <p class="text-muted">No visualization packages found.</p>
            </div>

            <div v-else>
                <VisualizationCard
                    v-for="viz in filteredInstalledVisualizations"
                    :key="viz.id"
                    :visualization="viz"
                    :loading-actions="loadingActions"
                    class="mb-3"
                    @toggle="handleToggle"
                    @update="handleUpdate"
                    @uninstall="handleUninstall"
                    @stage="handleStage"
                    @refresh="loadInstalledPackages" />
            </div>
        </div>

        <!-- Available Visualizations Tab -->
        <div v-if="activeTab === 'available'">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h3>Available Visualization Packages</h3>
                <b-input-group style="max-width: 300px">
                    <b-form-input
                        v-model="availableSearchFilter"
                        placeholder="Search packages..."
                        @input="searchAvailablePackages" />
                    <b-input-group-append>
                        <b-button
                            variant="outline-secondary"
                            @click="
                                availableSearchFilter = '';
                                searchAvailablePackages();
                            ">
                            <FontAwesomeIcon :icon="faTimes" />
                        </b-button>
                    </b-input-group-append>
                </b-input-group>
            </div>

            <div v-if="loadingAvailable" class="text-center py-4">
                <b-spinner label="Loading..." />
                <p class="mt-2">Searching available packages...</p>
            </div>

            <div v-else-if="availableVisualizations.length === 0" class="text-center py-4">
                <p class="text-muted">No packages found. Try adjusting your search terms.</p>
            </div>

            <div v-else>
                <AvailableVisualizationCard
                    v-for="viz in availableVisualizations"
                    :key="viz.name"
                    :package-data="viz"
                    :installed-packages="installedVisualizations"
                    :loading-actions="loadingActions"
                    class="mb-3"
                    @install="handleInstall" />
            </div>
        </div>

        <!-- Usage Stats Tab -->
        <div v-if="activeTab === 'usage'">
            <UsageStatsView :loading="loadingStats" :stats="usageStats" @refresh="loadUsageStats" />
        </div>

        <!-- Staging Tab -->
        <div v-if="activeTab === 'staging'">
            <div class="row">
                <div class="col-md-6">
                    <b-card>
                        <template v-slot:header>
                            <h5 class="card-title mb-0">
                                <FontAwesomeIcon :icon="faUpload" class="mr-2" />
                                Stage Assets
                            </h5>
                        </template>

                        <p class="text-muted">
                            Staging copies visualization assets from <code>config/plugins/visualizations</code> to
                            <code>static/plugins/visualizations</code> where Galaxy can serve them.
                        </p>
                        <div class="d-flex">
                            <b-button variant="primary" class="mr-2" :disabled="stagingLoading" @click="stageAllAssets">
                                <FontAwesomeIcon :icon="faUpload" :spin="stagingLoading" class="mr-1" />
                                Stage All Visualizations
                            </b-button>
                            <b-button variant="warning" :disabled="stagingLoading" @click="cleanStagedAssetsAction">
                                <FontAwesomeIcon :icon="faTrash" class="mr-1" />
                                Clean Staged Assets
                            </b-button>
                        </div>
                    </b-card>
                </div>
                <div class="col-md-6">
                    <b-card>
                        <template v-slot:header>
                            <h5 class="card-title mb-0">
                                <FontAwesomeIcon :icon="faInfoCircle" class="mr-2" />
                                Staging Status
                            </h5>
                        </template>

                        <div v-if="stagingStatus">
                            <p class="mb-2">
                                <strong>{{ stagingStatus.staged_count }}</strong> visualizations staged
                            </p>
                            <p class="mb-2 text-muted">
                                Total size: {{ bytesToString(stagingStatus.total_size, true, 2) }}
                            </p>
                            <div v-if="stagingStatus.staged_visualizations.length > 0" class="mt-3">
                                <h6>Staged Visualizations:</h6>
                                <div class="staged-viz-list" style="max-height: 200px; overflow-y: auto">
                                    <div
                                        v-for="viz in stagingStatus.staged_visualizations"
                                        :key="viz.name"
                                        class="d-flex justify-content-between align-items-center border-bottom py-1">
                                        <span class="small">{{ viz.name }}</span>
                                        <span class="text-muted small">{{ bytesToString(viz.size, true, 2) }}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div v-else class="text-center">
                            <b-spinner small />
                            Loading staging status...
                        </div>
                        <div class="mt-3">
                            <b-button size="sm" variant="outline-secondary" @click="loadStagingStatus">
                                <FontAwesomeIcon :icon="faSync" class="mr-1" />
                                Refresh Status
                            </b-button>
                        </div>
                    </b-card>
                </div>
            </div>
        </div>

        <!-- Install Modal -->
        <InstallVisualizationModal
            :show="showInstallModal"
            :package-data="selectedVisualization"
            :installing="installing"
            @confirm="confirmInstall"
            @cancel="showInstallModal = false" />
    </div>
</template>

<script setup lang="ts">
import {
    faChartBar,
    faDownload,
    faInfoCircle,
    faList,
    faServer,
    faSync,
    faTimes,
    faTrash,
    faUpload,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, onMounted, reactive, ref, watch } from "vue";

import { useConfirmDialog } from "@/composables/confirmDialog";
import { useToast } from "@/composables/toast";
import { bytesToString } from "@/utils/utils";

import type { AvailableVisualization, StagingStatus, UsageStats, Visualization } from "./services";
import {
    cleanStagedAssets,
    getAvailableVisualizations,
    getInstalledVisualizations,
    getStagingStatus,
    getVisualizationUsageStats,
    installVisualization,
    reloadVisualizationRegistry,
    stageAllVisualizations,
    stageVisualization,
    toggleVisualization,
    uninstallVisualization,
    updateVisualization,
} from "./services";

import AvailableVisualizationCard from "./AvailableVisualizationCard.vue";
import InstallVisualizationModal from "./InstallVisualizationModal.vue";
import UsageStatsView from "./UsageStatsView.vue";
import VisualizationCard from "./VisualizationCard.vue";
import Heading from "@/components/Common/Heading.vue";

const { confirm } = useConfirmDialog();
const toast = useToast();

const TAB_NAMES = ["installed", "available", "usage", "staging"] as const;
const activeTabIndex = ref(0);
const activeTab = computed(() => TAB_NAMES[activeTabIndex.value]!);

const loading = ref(false);
const loadingAvailable = ref(false);
const loadingStats = ref(false);
const loadingActions: Record<string, boolean> = reactive({});
const installing = ref(false);

const installedVisualizations = ref<Visualization[]>([]);
const filteredInstalledVisualizations = ref<Visualization[]>([]);
const showDisabled = ref(true);
const searchFilter = ref("");

const availableVisualizations = ref<AvailableVisualization[]>([]);
const availableSearchFilter = ref("");

const usageStats = ref<UsageStats>({ days: 30, stats: {} } as UsageStats);

const stagingLoading = ref(false);
const stagingStatus = ref<StagingStatus | null>(null);

const showInstallModal = ref(false);
const selectedVisualization = ref<AvailableVisualization | null>(null);

watch(showDisabled, () => {
    filterInstalled();
});

watch(activeTab, async (newTab) => {
    if (newTab === "available" && availableVisualizations.value.length === 0) {
        await loadAvailablePackages();
    } else if (newTab === "usage") {
        await loadUsageStats();
    } else if (newTab === "staging") {
        await loadStagingStatus();
    }
});

onMounted(async () => {
    await loadInstalledPackages();
});

function filterInstalled() {
    let filtered = installedVisualizations.value;

    if (!showDisabled.value) {
        filtered = filtered.filter((viz) => viz.enabled);
    }

    if (searchFilter.value) {
        const searchLower = searchFilter.value.toLowerCase();
        filtered = filtered.filter(
            (viz) =>
                viz.id.toLowerCase().includes(searchLower) ||
                viz.package.toLowerCase().includes(searchLower) ||
                (viz.metadata?.description && (viz.metadata.description as string).toLowerCase().includes(searchLower)),
        );
    }

    filteredInstalledVisualizations.value = filtered;
}

async function loadInstalledPackages() {
    loading.value = true;
    try {
        installedVisualizations.value = await getInstalledVisualizations(showDisabled.value);
        filterInstalled();
    } catch (error) {
        toast.error("Failed to load installed visualizations");
        console.error("Error loading installed visualizations:", error);
    } finally {
        loading.value = false;
    }
}

async function loadAvailablePackages() {
    loadingAvailable.value = true;
    try {
        availableVisualizations.value = await getAvailableVisualizations(availableSearchFilter.value);
    } catch (error) {
        toast.error("Failed to load available visualizations");
        console.error("Error loading available visualizations:", error);
    } finally {
        loadingAvailable.value = false;
    }
}

async function loadUsageStats() {
    loadingStats.value = true;
    try {
        usageStats.value = await getVisualizationUsageStats(30);
    } catch (error) {
        toast.error("Failed to load usage statistics");
        console.error("Error loading usage stats:", error);
    } finally {
        loadingStats.value = false;
    }
}

async function searchAvailablePackages() {
    await loadAvailablePackages();
}

async function handleToggle(viz: Visualization) {
    const actionKey = `toggle-${viz.id}`;
    loadingActions[actionKey] = true;

    try {
        await toggleVisualization(viz.id, !viz.enabled);
        toast.success(`Visualization ${viz.id} ${!viz.enabled ? "enabled" : "disabled"} successfully`);
        await loadInstalledPackages();
    } catch (error) {
        toast.error(`Failed to toggle visualization ${viz.id}`);
        console.error("Error toggling visualization:", error);
    } finally {
        delete loadingActions[actionKey];
    }
}

async function handleUpdate(viz: Visualization, newVersion: string) {
    const actionKey = `update-${viz.id}`;
    loadingActions[actionKey] = true;

    try {
        await updateVisualization(viz.id, newVersion);
        toast.success(`Visualization ${viz.id} updated to version ${newVersion}`);
        await loadInstalledPackages();
    } catch (error) {
        toast.error(`Failed to update visualization ${viz.id}`);
        console.error("Error updating visualization:", error);
    } finally {
        delete loadingActions[actionKey];
    }
}

async function handleUninstall(viz: Visualization) {
    const confirmed = await confirm(`Are you sure you want to uninstall ${viz.id}?`);
    if (!confirmed) {
        return;
    }

    const actionKey = `uninstall-${viz.id}`;
    loadingActions[actionKey] = true;

    try {
        await uninstallVisualization(viz.id);
        toast.success(`Visualization ${viz.id} uninstalled successfully`);
        await loadInstalledPackages();
    } catch (error) {
        toast.error(`Failed to uninstall visualization ${viz.id}`);
        console.error("Error uninstalling visualization:", error);
    } finally {
        delete loadingActions[actionKey];
    }
}

async function handleStage(viz: Visualization) {
    const actionKey = `stage-${viz.id}`;
    loadingActions[actionKey] = true;

    try {
        const result = await stageVisualization(viz.id);
        toast.success(result.message);

        if (activeTab.value === "staging") {
            await loadStagingStatus();
        }
    } catch (error) {
        toast.error(`Failed to stage visualization ${viz.id}`);
        console.error("Error staging visualization:", error);
    } finally {
        delete loadingActions[actionKey];
    }
}

function handleInstall(viz: AvailableVisualization) {
    selectedVisualization.value = viz;
    showInstallModal.value = true;
}

async function confirmInstall(vizId: string) {
    installing.value = true;

    try {
        await installVisualization(vizId, selectedVisualization.value!.name, selectedVisualization.value!.version);
        toast.success(`Visualization ${vizId} installed successfully`);
        showInstallModal.value = false;
        await loadInstalledPackages();
    } catch (error) {
        toast.error(`Failed to install visualization ${vizId}`);
        console.error("Error installing visualization:", error);
    } finally {
        installing.value = false;
    }
}

async function reloadRegistry() {
    loading.value = true;
    try {
        await reloadVisualizationRegistry();
        toast.success("Visualization registry reloaded successfully");
        await loadInstalledPackages();
    } catch (error) {
        toast.error("Failed to reload visualization registry");
        console.error("Error reloading registry:", error);
    } finally {
        loading.value = false;
    }
}

async function loadStagingStatus() {
    try {
        stagingStatus.value = await getStagingStatus();
    } catch (error) {
        toast.error("Failed to load staging status");
        console.error("Error loading staging status:", error);
    }
}

async function stageAllAssets() {
    stagingLoading.value = true;
    try {
        const result = await stageAllVisualizations();
        toast.success(result.message);
        await loadStagingStatus();
    } catch (error) {
        toast.error("Failed to stage visualizations");
        console.error("Error staging visualizations:", error);
    } finally {
        stagingLoading.value = false;
    }
}

async function cleanStagedAssetsAction() {
    const confirmed = await confirm(
        "Are you sure you want to clean all staged assets? This will remove all visualizations from Galaxy's serving directory.",
    );
    if (!confirmed) {
        return;
    }

    stagingLoading.value = true;
    try {
        const result = await cleanStagedAssets();
        toast.success(result.message);
        await loadStagingStatus();
    } catch (error) {
        toast.error("Failed to clean staged assets");
        console.error("Error cleaning staged assets:", error);
    } finally {
        stagingLoading.value = false;
    }
}
</script>
