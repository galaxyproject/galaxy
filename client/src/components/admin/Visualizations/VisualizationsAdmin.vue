<template>
    <div aria-labelledby="visualizations-admin-heading">
        <h1 id="visualizations-admin-heading" class="h-lg">Visualizations Management</h1>

        <Message :message="message" :status="messageStatus" />

        <div class="mb-3">
            <b-button-group>
                <b-button
                    :variant="activeTab === 'installed' ? 'primary' : 'outline-primary'"
                    @click="activeTab = 'installed'">
                    <i class="fa fa-list mr-1"></i>
                    Installed ({{ installedVisualizations.length }})
                </b-button>
                <b-button
                    :variant="activeTab === 'available' ? 'primary' : 'outline-primary'"
                    @click="activeTab = 'available'">
                    <i class="fa fa-download mr-1"></i>
                    Available
                </b-button>
                <b-button :variant="activeTab === 'usage' ? 'primary' : 'outline-primary'" @click="activeTab = 'usage'">
                    <i class="fa fa-chart-bar mr-1"></i>
                    Usage Stats
                </b-button>
                <b-button
                    :variant="activeTab === 'staging' ? 'primary' : 'outline-primary'"
                    @click="activeTab = 'staging'">
                    <i class="fa fa-server mr-1"></i>
                    Staging
                </b-button>
            </b-button-group>

            <b-button
                v-if="activeTab === 'installed'"
                variant="outline-secondary"
                class="ml-2"
                :disabled="loading"
                @click="reloadRegistry">
                <i class="fa fa-sync mr-1" :class="{ 'fa-spin': loading }"></i>
                Reload Registry
            </b-button>
        </div>

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
                                <i class="fa fa-times"></i>
                            </b-button>
                        </b-input-group-append>
                    </b-input-group>
                </div>
            </div>

            <div v-if="loading" class="text-center py-4">
                <b-spinner label="Loading..."></b-spinner>
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
                            <i class="fa fa-times"></i>
                        </b-button>
                    </b-input-group-append>
                </b-input-group>
            </div>

            <div v-if="loadingAvailable" class="text-center py-4">
                <b-spinner label="Loading..."></b-spinner>
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
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fa fa-upload mr-2"></i>
                                Stage Assets
                            </h5>
                        </div>
                        <div class="card-body">
                            <p class="text-muted">
                                Staging copies visualization assets from <code>config/plugins/visualizations</code> to
                                <code>static/plugins/visualizations</code> where Galaxy can serve them.
                            </p>
                            <div class="d-flex gap-2">
                                <b-button variant="primary" :disabled="stagingLoading" @click="stageAllAssets">
                                    <i class="fa fa-upload mr-1" :class="{ 'fa-spin': stagingLoading }"></i>
                                    Stage All Visualizations
                                </b-button>
                                <b-button variant="warning" :disabled="stagingLoading" @click="cleanStagedAssets">
                                    <i class="fa fa-trash mr-1"></i>
                                    Clean Staged Assets
                                </b-button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fa fa-info-circle mr-2"></i>
                                Staging Status
                            </h5>
                        </div>
                        <div class="card-body">
                            <div v-if="stagingStatus">
                                <p class="mb-2">
                                    <strong>{{ stagingStatus.staged_count }}</strong> visualizations staged
                                </p>
                                <p class="mb-2 text-muted">
                                    Total size: {{ formatFileSize(stagingStatus.total_size) }}
                                </p>
                                <div v-if="stagingStatus.staged_visualizations.length > 0" class="mt-3">
                                    <h6>Staged Visualizations:</h6>
                                    <div class="staged-viz-list" style="max-height: 200px; overflow-y: auto">
                                        <div
                                            v-for="viz in stagingStatus.staged_visualizations"
                                            :key="viz.name"
                                            class="d-flex justify-content-between align-items-center border-bottom py-1">
                                            <span class="small">{{ viz.name }}</span>
                                            <span class="text-muted small">{{ formatFileSize(viz.size) }}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div v-else class="text-center">
                                <b-spinner small></b-spinner>
                                Loading staging status...
                            </div>
                            <div class="mt-3">
                                <b-button size="sm" variant="outline-secondary" @click="loadStagingStatus">
                                    <i class="fa fa-sync mr-1"></i>
                                    Refresh Status
                                </b-button>
                            </div>
                        </div>
                    </div>
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

<script>
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

import Message from "../../Message.vue";
import AvailableVisualizationCard from "./AvailableVisualizationCard.vue";
import InstallVisualizationModal from "./InstallVisualizationModal.vue";
import UsageStatsView from "./UsageStatsView.vue";
import VisualizationCard from "./VisualizationCard.vue";

export default {
    name: "VisualizationsAdmin",

    components: {
        Message,
        VisualizationCard,
        AvailableVisualizationCard,
        InstallVisualizationModal,
        UsageStatsView,
    },

    data() {
        return {
            activeTab: "installed",
            loading: false,
            loadingAvailable: false,
            loadingStats: false,
            loadingActions: new Set(),
            installing: false,
            message: "",
            messageStatus: "",

            // Installed packages
            installedVisualizations: [],
            filteredInstalledVisualizations: [],
            showDisabled: true,
            searchFilter: "",

            // Available packages
            availableVisualizations: [],
            availableSearchFilter: "",

            // Usage stats
            usageStats: { days: 30, stats: {} },

            // Staging
            stagingLoading: false,
            stagingStatus: null,

            // Install modal
            showInstallModal: false,
            selectedVisualization: null,
        };
    },

    watch: {
        showDisabled() {
            this.filterInstalled();
        },

        async activeTab(newTab) {
            if (newTab === "available" && this.availableVisualizations.length === 0) {
                await this.loadAvailablePackages();
            } else if (newTab === "usage") {
                await this.loadUsageStats();
            } else if (newTab === "staging") {
                await this.loadStagingStatus();
            }
        },
    },

    async mounted() {
        await this.loadInstalledPackages();
        await this.loadAvailablePackages();
    },

    methods: {
        async loadInstalledPackages() {
            this.loading = true;
            try {
                this.installedVisualizations = await getInstalledVisualizations(this.showDisabled);
                this.filterInstalled();
                this.clearMessage();
            } catch (error) {
                this.showMessage("Failed to load installed visualizations", "error");
                console.error("Error loading installed visualizations:", error);
            } finally {
                this.loading = false;
            }
        },

        async loadAvailablePackages() {
            this.loadingAvailable = true;
            try {
                this.availableVisualizations = await getAvailableVisualizations(this.availableSearchFilter);
                this.clearMessage();
            } catch (error) {
                this.showMessage("Failed to load available visualizations", "error");
                console.error("Error loading available visualizations:", error);
            } finally {
                this.loadingAvailable = false;
            }
        },

        async loadUsageStats() {
            this.loadingStats = true;
            try {
                this.usageStats = await getVisualizationUsageStats(30);
                this.clearMessage();
            } catch (error) {
                this.showMessage("Failed to load usage statistics", "error");
                console.error("Error loading usage stats:", error);
            } finally {
                this.loadingStats = false;
            }
        },

        filterInstalled() {
            let filtered = this.installedVisualizations;

            // Filter by enabled/disabled
            if (!this.showDisabled) {
                filtered = filtered.filter((viz) => viz.enabled);
            }

            // Filter by search term
            if (this.searchFilter) {
                const searchLower = this.searchFilter.toLowerCase();
                filtered = filtered.filter(
                    (viz) =>
                        viz.id.toLowerCase().includes(searchLower) ||
                        viz.package.toLowerCase().includes(searchLower) ||
                        (viz.metadata?.description && viz.metadata.description.toLowerCase().includes(searchLower))
                );
            }

            this.filteredInstalledVisualizations = filtered;
        },

        async searchAvailablePackages() {
            await this.loadAvailablePackages();
        },

        async handleToggle(viz) {
            const actionKey = `toggle-${viz.id}`;
            this.loadingActions.add(actionKey);

            try {
                await toggleVisualization(viz.id, !viz.enabled);
                this.showMessage(
                    `Visualization ${viz.id} ${!viz.enabled ? "enabled" : "disabled"} successfully`,
                    "success"
                );
                await this.loadInstalledPackages();
            } catch (error) {
                this.showMessage(`Failed to toggle visualization ${viz.id}`, "error");
                console.error("Error toggling visualization:", error);
            } finally {
                this.loadingActions.delete(actionKey);
            }
        },

        async handleUpdate(viz, newVersion) {
            const actionKey = `update-${viz.id}`;
            this.loadingActions.add(actionKey);

            try {
                await updateVisualization(viz.id, newVersion);
                this.showMessage(`Visualization ${viz.id} updated to version ${newVersion}`, "success");
                await this.loadInstalledPackages();
            } catch (error) {
                this.showMessage(`Failed to update visualization ${viz.id}`, "error");
                console.error("Error updating visualization:", error);
            } finally {
                this.loadingActions.delete(actionKey);
            }
        },

        async handleUninstall(viz) {
            if (!confirm(`Are you sure you want to uninstall ${viz.id}?`)) {
                return;
            }

            const actionKey = `uninstall-${viz.id}`;
            this.loadingActions.add(actionKey);

            try {
                await uninstallVisualization(viz.id);
                this.showMessage(`Visualization ${viz.id} uninstalled successfully`, "success");
                await this.loadInstalledPackages();
            } catch (error) {
                this.showMessage(`Failed to uninstall visualization ${viz.id}`, "error");
                console.error("Error uninstalling visualization:", error);
            } finally {
                this.loadingActions.delete(actionKey);
            }
        },

        async handleStage(viz) {
            const actionKey = `stage-${viz.id}`;
            this.loadingActions.add(actionKey);

            try {
                const result = await stageVisualization(viz.id);
                this.showMessage(result.message, "success");

                // Refresh staging status if we're on the staging tab
                if (this.activeTab === "staging") {
                    await this.loadStagingStatus();
                }
            } catch (error) {
                this.showMessage(`Failed to stage visualization ${viz.id}`, "error");
                console.error("Error staging visualization:", error);
            } finally {
                this.loadingActions.delete(actionKey);
            }
        },

        handleInstall(viz) {
            this.selectedVisualization = viz;
            this.showInstallModal = true;
        },

        async confirmInstall(vizId) {
            this.installing = true;

            try {
                await installVisualization(vizId, this.selectedVisualization.name, this.selectedVisualization.version);
                this.showMessage(`Visualization ${vizId} installed successfully`, "success");
                this.showInstallModal = false;
                await this.loadInstalledPackages();
            } catch (error) {
                this.showMessage(`Failed to install visualization ${vizId}`, "error");
                console.error("Error installing visualization:", error);
            } finally {
                this.installing = false;
            }
        },

        async reloadRegistry() {
            this.loading = true;
            try {
                await reloadVisualizationRegistry();
                this.showMessage("Visualization registry reloaded successfully", "success");
                await this.loadInstalledPackages();
            } catch (error) {
                this.showMessage("Failed to reload visualization registry", "error");
                console.error("Error reloading registry:", error);
            } finally {
                this.loading = false;
            }
        },

        // Staging methods
        async loadStagingStatus() {
            try {
                this.stagingStatus = await getStagingStatus();
            } catch (error) {
                this.showMessage("Failed to load staging status", "error");
                console.error("Error loading staging status:", error);
            }
        },

        async stageAllAssets() {
            this.stagingLoading = true;
            try {
                const result = await stageAllVisualizations();
                this.showMessage(result.message, "success");
                await this.loadStagingStatus();
            } catch (error) {
                this.showMessage("Failed to stage visualizations", "error");
                console.error("Error staging visualizations:", error);
            } finally {
                this.stagingLoading = false;
            }
        },

        async cleanStagedAssets() {
            if (
                !confirm(
                    "Are you sure you want to clean all staged assets? This will remove all visualizations from Galaxy's serving directory."
                )
            ) {
                return;
            }

            this.stagingLoading = true;
            try {
                const result = await cleanStagedAssets();
                this.showMessage(result.message, "success");
                await this.loadStagingStatus();
            } catch (error) {
                this.showMessage("Failed to clean staged assets", "error");
                console.error("Error cleaning staged assets:", error);
            } finally {
                this.stagingLoading = false;
            }
        },

        formatFileSize(bytes) {
            if (bytes === 0) {
                return "0 B";
            }
            const k = 1024;
            const sizes = ["B", "KB", "MB", "GB"];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
        },

        showMessage(text, status) {
            this.message = text;
            this.messageStatus = status;
        },

        clearMessage() {
            this.message = "";
            this.messageStatus = "";
        },
    },
};
</script>

<style scoped>
.card {
    border: 1px solid #dee2e6;
    border-radius: 0.375rem;
}

.card-header {
    background-color: #f8f9fa;
    border-bottom: 1px solid #dee2e6;
    padding: 0.75rem 1rem;
}

.card-body {
    padding: 1rem;
}

.btn-group .btn {
    border-radius: 0.375rem;
}

.btn-group .btn:not(:last-child) {
    margin-right: 0.5rem;
}

.input-group {
    box-shadow: none;
}

.spinner-border-sm {
    width: 1rem;
    height: 1rem;
}
</style>
