<template>
    <b-card class="visualization-card">
        <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
                <div class="d-flex align-items-center mb-2">
                    <h5 class="mb-0 mr-2">{{ visualization.id }}</h5>
                    <b-badge :variant="visualization.enabled ? 'success' : 'secondary'" class="mr-2">
                        {{ visualization.enabled ? "Enabled" : "Disabled" }}
                    </b-badge>
                    <b-badge :variant="visualization.installed ? 'primary' : 'warning'" class="mr-2">
                        {{ visualization.installed ? "Installed" : "Not Installed" }}
                    </b-badge>
                </div>

                <div class="text-muted mb-2">
                    <div class="d-flex flex-wrap">
                        <span class="mr-3"> <strong>Package:</strong> {{ visualization.package }} </span>
                        <span class="mr-3"> <strong>Version:</strong> {{ visualization.version }} </span>
                        <span v-if="visualization.size" class="mr-3">
                            <strong>Size:</strong> {{ formatSize(visualization.size) }}
                        </span>
                    </div>
                </div>

                <div v-if="visualization.metadata?.description" class="mb-2">
                    <p class="text-muted mb-1">{{ visualization.metadata.description }}</p>
                </div>

                <div v-if="visualization.metadata" class="small text-muted">
                    <div class="d-flex flex-wrap">
                        <span v-if="visualization.metadata.author" class="mr-3">
                            <strong>Author:</strong> {{ visualization.metadata.author }}
                        </span>
                        <span v-if="visualization.metadata.license" class="mr-3">
                            <strong>License:</strong> {{ visualization.metadata.license }}
                        </span>
                        <span v-if="visualization.metadata.homepage" class="mr-3">
                            <a :href="visualization.metadata.homepage" target="_blank" rel="noopener">
                                Homepage
                                <i class="fa fa-external-link-alt fa-sm"></i>
                            </a>
                        </span>
                    </div>
                </div>

                <!-- Dependencies -->
                <div
                    v-if="
                        visualization.metadata?.dependencies &&
                        Object.keys(visualization.metadata.dependencies).length > 0
                    "
                    class="mt-2">
                    <b-button v-b-toggle="`deps-${visualization.id}`" variant="link" size="sm" class="p-0 text-info">
                        <i class="fa fa-caret-right fa-fw"></i>
                        Dependencies ({{ Object.keys(visualization.metadata.dependencies).length }})
                    </b-button>
                    <b-collapse :id="`deps-${visualization.id}`" class="mt-2">
                        <div class="small">
                            <div
                                v-for="(version, dep) in visualization.metadata.dependencies"
                                :key="`dep-${dep}`"
                                class="mb-1">
                                <code>{{ dep }}@{{ version }}</code>
                            </div>
                        </div>
                    </b-collapse>
                </div>
            </div>

            <div class="ml-3">
                <b-dropdown variant="outline-secondary" size="sm" right text="Actions" :disabled="isLoading">
                    <b-dropdown-item :disabled="isLoading" @click="$emit('toggle', visualization)">
                        <i class="fa fa-fw" :class="visualization.enabled ? 'fa-eye-slash' : 'fa-eye'"></i>
                        {{ visualization.enabled ? "Disable" : "Enable" }}
                    </b-dropdown-item>

                    <b-dropdown-item
                        v-if="visualization.installed"
                        :disabled="isLoading"
                        @click="showUpdateModal = true">
                        <i class="fa fa-fw fa-arrow-up"></i>
                        Update
                    </b-dropdown-item>

                    <b-dropdown-item :disabled="isLoading" @click="$emit('stage', visualization)">
                        <i class="fa fa-fw fa-upload"></i>
                        Stage Assets
                    </b-dropdown-item>

                    <b-dropdown-item
                        v-if="visualization.installed"
                        :disabled="isLoading"
                        variant="danger"
                        @click="$emit('uninstall', visualization)">
                        <i class="fa fa-fw fa-trash"></i>
                        Uninstall
                    </b-dropdown-item>

                    <b-dropdown-divider v-if="visualization.installed"></b-dropdown-divider>

                    <b-dropdown-item :disabled="isLoading" @click="showDetails = !showDetails">
                        <i class="fa fa-fw fa-info-circle"></i>
                        {{ showDetails ? "Hide Details" : "Show Details" }}
                    </b-dropdown-item>
                </b-dropdown>
            </div>
        </div>

        <!-- Details Section -->
        <b-collapse v-model="showDetails" class="mt-3">
            <hr />
            <div class="small">
                <div class="row">
                    <div class="col-md-6">
                        <div v-if="visualization.path" class="mb-2">
                            <strong>Installation Path:</strong>
                            <br />
                            <code class="small">{{ visualization.path }}</code>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div v-if="visualization.metadata" class="mb-2">
                            <strong>Package Metadata:</strong>
                            <br />
                            <pre class="small bg-light p-2 rounded">{{
                                JSON.stringify(visualization.metadata, null, 2)
                            }}</pre>
                        </div>
                    </div>
                </div>
            </div>
        </b-collapse>

        <!-- Update Modal -->
        <b-modal
            v-model="showUpdateModal"
            title="Update Visualization"
            :ok-disabled="!updateVersion || updating"
            ok-title="Update"
            @ok="handleUpdate">
            <div v-if="updating" class="text-center">
                <b-spinner label="Updating..."></b-spinner>
                <p class="mt-2">Updating visualization package...</p>
            </div>

            <div v-else>
                <p>
                    Update <strong>{{ visualization.id }}</strong> to a new version:
                </p>

                <b-form-group label="New Version:" label-for="version-input">
                    <b-form-input
                        id="version-input"
                        v-model="updateVersion"
                        placeholder="e.g., 1.2.3"
                        :state="updateVersion ? true : null"></b-form-input>
                    <b-form-text> Current version: {{ visualization.version }} </b-form-text>
                </b-form-group>
            </div>
        </b-modal>
    </b-card>
</template>

<script>
export default {
    name: "VisualizationCard",

    props: {
        visualization: {
            type: Object,
            required: true,
        },
        loadingActions: {
            type: Set,
            default: () => new Set(),
        },
    },

    data() {
        return {
            showDetails: false,
            showUpdateModal: false,
            updateVersion: "",
            updating: false,
        };
    },

    computed: {
        isLoading() {
            return (
                this.loadingActions.has(`toggle-${this.visualization.id}`) ||
                this.loadingActions.has(`update-${this.visualization.id}`) ||
                this.loadingActions.has(`uninstall-${this.visualization.id}`) ||
                this.loadingActions.has(`stage-${this.visualization.id}`) ||
                this.updating
            );
        },
    },

    watch: {
        showUpdateModal(isShown) {
            if (!isShown) {
                this.updateVersion = "";
                this.updating = false;
            }
        },
    },

    methods: {
        formatSize(bytes) {
            if (bytes === 0) {
                return "0 B";
            }
            const k = 1024;
            const sizes = ["B", "KB", "MB", "GB"];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
        },

        async handleUpdate() {
            if (!this.updateVersion) {
                return;
            }

            this.updating = true;
            try {
                this.$emit("update", this.visualization, this.updateVersion);
                this.showUpdateModal = false;
                this.updateVersion = "";
            } catch (error) {
                console.error("Error in update handler:", error);
            } finally {
                this.updating = false;
            }
        },
    },
};
</script>

<style scoped>
.visualization-card {
    transition: box-shadow 0.15s ease-in-out;
}

.visualization-card:hover {
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

.badge {
    font-size: 0.75em;
}

.btn-link {
    text-decoration: none;
}

.btn-link:hover {
    text-decoration: underline;
}

code {
    font-size: 0.875em;
    color: #6f42c1;
}

pre {
    font-size: 0.75rem;
    max-height: 200px;
    overflow-y: auto;
}

.collapse-content {
    border-top: 1px solid #dee2e6;
    margin-top: 1rem;
    padding-top: 1rem;
}
</style>
