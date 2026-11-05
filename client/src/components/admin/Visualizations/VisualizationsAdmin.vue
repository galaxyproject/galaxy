<template>
    <div aria-labelledby="visualizations-admin-heading">
        <Heading id="visualizations-admin-heading" h1 size="lg">Visualizations Management</Heading>

        <p class="text-muted mb-3">
            Install and manage visualization packages from the npm registry. Installed packages live in Galaxy's managed
            package store and are served from there, alongside the visualizations Galaxy ships with.
        </p>

        <GTabs v-model="activeTabIndex" class="mb-3">
            <GTab>
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faList" class="mr-1" />
                    Installed ({{ installedVisualizations.length }})
                </template>
            </GTab>
            <GTab>
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faDownload" class="mr-1" />
                    Available
                </template>
            </GTab>
        </GTabs>

        <!-- Installed Visualizations Tab -->
        <div v-if="activeTab === 'installed'">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div class="d-flex align-items-center">
                    <GCheckbox v-model="showDisabled" class="mr-3"> Show disabled visualizations </GCheckbox>
                    <GButton outline size="small" :disabled="loading" @click="reloadRegistry">
                        <FontAwesomeIcon :icon="faSync" :spin="loading" class="mr-1" />
                        Refresh
                    </GButton>
                </div>
                <div class="d-flex align-items-center">
                    <GFormInput v-model="searchFilter" placeholder="Filter visualizations..." aria-label="Filter" />
                    <GButton outline icon-only class="ml-1" title="Clear filter" @click="searchFilter = ''">
                        <FontAwesomeIcon :icon="faTimes" />
                    </GButton>
                </div>
            </div>

            <div v-if="loading" class="text-center py-4">
                <LoadingSpan message="Loading visualization packages" />
            </div>

            <div v-else-if="filteredInstalledVisualizations.length === 0" class="text-center py-4">
                <p v-if="installedVisualizations.length === 0 && !searchFilter" class="text-muted mb-2">
                    No visualization packages installed yet.
                </p>
                <p v-if="installedVisualizations.length === 0 && !searchFilter" class="text-muted">
                    Browse the
                    <GLink @click="activeTabIndex = 1">Available</GLink>
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
                    class="mb-3"
                    @toggle="handleToggle"
                    @update="handleUpdate"
                    @uninstall="handleUninstall"
                    @refresh="loadInstalledPackages" />
            </div>
        </div>

        <!-- Available Visualizations Tab -->
        <div v-if="activeTab === 'available'">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <Heading h3 size="sm">Available Visualization Packages</Heading>
                <div class="d-flex align-items-center" style="max-width: 300px">
                    <GFormInput
                        v-model="availableSearchFilter"
                        placeholder="Search packages..."
                        aria-label="Search packages"
                        @update:modelValue="searchAvailablePackages" />
                    <GButton
                        outline
                        icon-only
                        class="ml-1"
                        title="Clear search"
                        @click="
                            availableSearchFilter = '';
                            searchAvailablePackages();
                        ">
                        <FontAwesomeIcon :icon="faTimes" />
                    </GButton>
                </div>
            </div>

            <div v-if="loadingAvailable" class="text-center py-4">
                <LoadingSpan message="Searching the npm registry for @galaxyproject packages" />
            </div>

            <GAlert v-else-if="availableLoadError" variant="warning">
                Could not reach the npm registry. Check that this Galaxy server has internet access.
            </GAlert>

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
import { faDownload, faList, faSync, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useDebounceFn } from "@vueuse/core";
import { computed, onMounted, reactive, ref, watch } from "vue";

import { useConfirmDialog } from "@/composables/confirmDialog";
import { useToast } from "@/composables/toast";

import type { AvailableVisualization, Visualization } from "./services";
import {
    getAvailableVisualizations,
    getInstalledVisualizations,
    installVisualization,
    reloadVisualizationRegistry,
    toggleVisualization,
    uninstallVisualization,
    updateVisualization,
} from "./services";

import AvailableVisualizationCard from "./AvailableVisualizationCard.vue";
import InstallVisualizationModal from "./InstallVisualizationModal.vue";
import VisualizationCard from "./VisualizationCard.vue";
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import GTab from "@/components/BaseComponents/GTab.vue";
import GTabs from "@/components/BaseComponents/GTabs.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const { confirm } = useConfirmDialog();
const toast = useToast();

const TAB_NAMES = ["installed", "available"] as const;
const activeTabIndex = ref(0);
const activeTab = computed(() => TAB_NAMES[activeTabIndex.value]!);

const loading = ref(false);
const loadingAvailable = ref(false);
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

const showInstallModal = ref(false);
const selectedVisualization = ref<AvailableVisualization | null>(null);

watch(activeTab, async (newTab) => {
    if (newTab === "available" && availableVisualizations.value.length === 0) {
        await loadAvailablePackages();
    }
});

onMounted(async () => {
    await loadInstalledPackages();
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
        // always fetch everything; the Show disabled checkbox filters locally
        installedVisualizations.value = await getInstalledVisualizations();
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

const searchAvailablePackages = useDebounceFn(loadAvailablePackages, 300);

async function handleToggle(viz: Visualization) {
    const actionKey = `toggle-${viz.id}`;
    loadingActions[actionKey] = true;

    try {
        await toggleVisualization(viz.id, !viz.enabled);
        toast.success(`Visualization ${viz.id} ${!viz.enabled ? "enabled" : "disabled"}`);
    } catch (error) {
        toast.error(`Failed to toggle ${viz.id}: ${errorMessage(error)}`);
    } finally {
        delete loadingActions[actionKey];
        await loadInstalledPackages();
    }
}

async function handleUpdate(viz: Visualization, newVersion: string) {
    const actionKey = `update-${viz.id}`;
    loadingActions[actionKey] = true;

    try {
        await updateVisualization(viz.id, newVersion);
        toast.success(`Updated ${viz.id} to version ${newVersion}`);
    } catch (error) {
        toast.error(`Failed to update ${viz.id}: ${errorMessage(error)}`);
    } finally {
        delete loadingActions[actionKey];
        await loadInstalledPackages();
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
    } catch (error) {
        toast.error(`Failed to uninstall ${viz.id}: ${errorMessage(error)}`);
    } finally {
        delete loadingActions[actionKey];
        await loadInstalledPackages();
    }
}

function handleInstall(viz: AvailableVisualization) {
    selectedVisualization.value = viz;
    showInstallModal.value = true;
}

async function confirmInstall() {
    const { name, version } = selectedVisualization.value!;
    installing.value = true;

    try {
        const installed = await installVisualization(name, version);
        showInstallModal.value = false;
        toast.success(`Installed ${installed.id}`);
    } catch (error) {
        toast.error(`Failed to install ${name}: ${errorMessage(error)}`);
    } finally {
        installing.value = false;
        await loadInstalledPackages();
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
</script>
