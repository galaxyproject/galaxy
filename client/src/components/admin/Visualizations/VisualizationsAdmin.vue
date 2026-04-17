<template>
    <div aria-labelledby="visualizations-admin-heading">
        <Heading id="visualizations-admin-heading" h1 size="lg">Visualizations Management</Heading>

        <p class="text-muted mb-3">
            Install and manage visualization packages from the npm registry. Installed packages are kept separately from
            Galaxy's served static assets and staged into the serving directory when needed.
        </p>

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

        <!-- Installed Visualizations Tab -->
        <div v-if="activeTab === 'installed'">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div class="d-flex align-items-center">
                    <b-form-checkbox v-model="showDisabled" class="mr-3">
                        Show disabled visualizations
                    </b-form-checkbox>
                    <b-button variant="outline-secondary" size="sm" :disabled="loading" @click="reloadRegistry">
                        <FontAwesomeIcon :icon="faSync" :spin="loading" class="mr-1" />
                        Refresh
                    </b-button>
                </div>
                <div>
                    <b-input-group>
                        <b-form-input v-model="searchFilter" placeholder="Filter visualizations..." />
                        <b-input-group-append>
                            <b-button variant="outline-secondary" aria-label="Clear filter" @click="searchFilter = ''">
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
                <p v-if="installedVisualizations.length === 0 && !searchFilter" class="text-muted mb-2">
                    No visualization packages installed yet.
                </p>
                <p v-if="installedVisualizations.length === 0 && !searchFilter" class="text-muted">
                    Browse the
                    <b-link @click="activeTabIndex = 1">Available</b-link>
                    tab to find and install visualization packages from the npm registry.
                </p>
                <p v-else class="text-muted">No visualizations match your filter.</p>
            </div>

            <div v-else>
                <VisualizationCard
                    v-for="viz in filteredInstalledVisualizations"
                    :key="viz.id"
                    :visualization="viz"
                    :loading-actions="loadingActions"
                    :staged-names="stagedNames"
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
                <Heading h3 size="sm">Available Visualization Packages</Heading>
                <b-input-group style="max-width: 300px">
                    <b-form-input
                        v-model="availableSearchFilter"
                        placeholder="Search packages..."
                        @input="searchAvailablePackages" />
                    <b-input-group-append>
                        <b-button
                            variant="outline-secondary"
                            aria-label="Clear search"
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
                <p class="mt-2">Searching npm registry for @galaxyproject packages...</p>
            </div>

            <b-alert v-else-if="availableLoadError" variant="warning" show>
                Could not reach the npm registry. Check that this Galaxy server has internet access.
            </b-alert>

            <div v-else-if="availableVisualizations.length === 0" class="text-center py-4">
                <p class="text-muted">
                    {{
                        availableSearchFilter
                            ? "No packages match your search."
                            : "No visualization packages found in the npm registry."
                    }}
                </p>
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
            <p class="text-muted mb-3">
                Staging copies visualization assets into Galaxy's static serving directory. Install and update actions
                automatically re-stage packages, and you can manually re-stage here if needed.
            </p>
            <div class="row">
                <div class="col-md-6">
                    <b-card>
                        <template v-slot:header>
                            <h5 class="card-title mb-0">
                                <FontAwesomeIcon :icon="faUpload" class="mr-2" />
                                Stage Assets
                            </h5>
                        </template>

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
                            <div v-if="stagingStatus.staged_visualizations?.length" class="mt-3">
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
            :installed-visualizations="installedVisualizations"
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
import { useDebounceFn } from "@vueuse/core";
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
const showDisabled = ref(true);
const searchFilter = ref("");

const filteredInstalledVisualizations = computed(() => {
    let filtered = installedVisualizations.value;
    if (!showDisabled.value) {
        filtered = filtered.filter((viz) => viz.enabled);
    }
    if (searchFilter.value) {
        const q = searchFilter.value.toLowerCase();
        filtered = filtered.filter(
            (viz) =>
                viz.id.toLowerCase().includes(q) ||
                viz.package.toLowerCase().includes(q) ||
                (viz.metadata?.description && (viz.metadata.description as string).toLowerCase().includes(q)),
        );
    }
    return filtered;
});

const availableVisualizations = ref<AvailableVisualization[]>([]);
const availableSearchFilter = ref("");
const availableLoadError = ref(false);

const usageStats = ref<UsageStats>({ days: 30, stats: {} } as UsageStats);

const stagingLoading = ref(false);
const stagingStatus = ref<StagingStatus | null>(null);
const stagedNames = computed(() => stagingStatus.value?.staged_visualizations?.map((v) => v.name) ?? []);

const showInstallModal = ref(false);
const selectedVisualization = ref<AvailableVisualization | null>(null);

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
    await Promise.all([loadInstalledPackages(), loadStagingStatus()]);
});

function errorMessage(error: unknown): string {
    if (error instanceof Error) {
        return error.message;
    }
    return String(error);
}

async function loadInstalledPackages() {
    loading.value = true;
    try {
        installedVisualizations.value = await getInstalledVisualizations(showDisabled.value);
    } catch (error) {
        toast.error(`Failed to load installed visualizations: ${errorMessage(error)}`);
    } finally {
        loading.value = false;
    }
}

async function loadAvailablePackages() {
    loadingAvailable.value = true;
    availableLoadError.value = false;
    try {
        availableVisualizations.value = await getAvailableVisualizations(availableSearchFilter.value);
    } catch (error) {
        availableLoadError.value = true;
        toast.error(`Failed to search npm registry: ${errorMessage(error)}`);
    } finally {
        loadingAvailable.value = false;
    }
}

async function loadUsageStats() {
    loadingStats.value = true;
    try {
        usageStats.value = await getVisualizationUsageStats(30);
    } catch (error) {
        toast.error(`Failed to load usage statistics: ${errorMessage(error)}`);
    } finally {
        loadingStats.value = false;
    }
}

const searchAvailablePackages = useDebounceFn(loadAvailablePackages, 300);

async function handleToggle(viz: Visualization) {
    const actionKey = `toggle-${viz.id}`;
    loadingActions[actionKey] = true;

    try {
        await toggleVisualization(viz.id, !viz.enabled);
        toast.success(`Visualization ${viz.id} ${!viz.enabled ? "enabled" : "disabled"}`);
        await loadInstalledPackages();
    } catch (error) {
        toast.error(`Failed to toggle ${viz.id}: ${errorMessage(error)}`);
    } finally {
        delete loadingActions[actionKey];
    }
}

async function handleUpdate(viz: Visualization, newVersion: string) {
    const actionKey = `update-${viz.id}`;
    loadingActions[actionKey] = true;

    try {
        await updateVisualization(viz.id, newVersion);
        await stageVisualization(viz.id);
        toast.success(`Updated and staged ${viz.id} to version ${newVersion}`);
        await loadInstalledPackages();
        await loadStagingStatus();
    } catch (error) {
        toast.error(`Failed to update ${viz.id}: ${errorMessage(error)}`);
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
        toast.success(`Uninstalled ${viz.id}`);
        await loadInstalledPackages();
        await loadStagingStatus();
    } catch (error) {
        toast.error(`Failed to uninstall ${viz.id}: ${errorMessage(error)}`);
    } finally {
        delete loadingActions[actionKey];
    }
}

async function handleStage(viz: Visualization) {
    const actionKey = `stage-${viz.id}`;
    loadingActions[actionKey] = true;

    try {
        await stageVisualization(viz.id);
        toast.success(`Staged ${viz.id}`);
        await loadStagingStatus();
    } catch (error) {
        toast.error(`Failed to stage ${viz.id}: ${errorMessage(error)}`);
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
        await stageVisualization(vizId);
        showInstallModal.value = false;
        toast.success(`Installed and staged ${vizId}`);
        await loadInstalledPackages();
        await loadStagingStatus();
    } catch (error) {
        toast.error(`Failed to install ${vizId}: ${errorMessage(error)}`);
    } finally {
        installing.value = false;
    }
}

async function reloadRegistry() {
    loading.value = true;
    try {
        await reloadVisualizationRegistry();
        toast.success("Visualization list refreshed");
        await loadInstalledPackages();
    } catch (error) {
        toast.error(`Failed to refresh: ${errorMessage(error)}`);
    } finally {
        loading.value = false;
    }
}

async function loadStagingStatus() {
    try {
        stagingStatus.value = await getStagingStatus();
    } catch (error) {
        toast.error(`Failed to load staging status: ${errorMessage(error)}`);
    }
}

async function stageAllAssets() {
    stagingLoading.value = true;
    try {
        const result = await stageAllVisualizations();
        toast.success(result.message);
        await loadStagingStatus();
    } catch (error) {
        toast.error(`Failed to stage visualizations: ${errorMessage(error)}`);
    } finally {
        stagingLoading.value = false;
    }
}

async function cleanStagedAssetsAction() {
    const confirmed = await confirm(
        "Are you sure? This removes all visualizations from Galaxy's serving directory until they are re-staged.",
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
        toast.error(`Failed to clean staged assets: ${errorMessage(error)}`);
    } finally {
        stagingLoading.value = false;
    }
}
</script>
