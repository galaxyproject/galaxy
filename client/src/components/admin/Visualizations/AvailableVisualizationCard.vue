<template>
    <b-card class="available-visualization-card">
        <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
                <div class="d-flex align-items-center mb-2">
                    <h5 class="mb-0 mr-2">{{ packageData.name }}</h5>
                    <b-badge variant="info" class="mr-2">v{{ packageData.version }}</b-badge>
                    <b-badge v-if="isInstalled" variant="success">Installed</b-badge>
                </div>

                <p v-if="packageData.description" class="text-muted mb-2">
                    {{ packageData.description }}
                </p>

                <div class="small text-muted mb-2">
                    <div class="d-flex flex-wrap">
                        <span v-if="packageData.keywords?.length" class="mr-3">
                            <strong>Keywords:</strong> {{ packageData.keywords.join(", ") }}
                        </span>
                        <span v-if="packageData.modified" class="mr-3">
                            <strong>Last Updated:</strong> {{ formatDate(packageData.modified) }}
                        </span>
                    </div>
                </div>

                <div v-if="packageData.maintainers?.length" class="small text-muted mb-2">
                    <strong>Maintainers:</strong>
                    <span v-for="(maintainer, index) in packageData.maintainers" :key="`maintainer-${index}`">
                        {{ maintainer.username || maintainer.email
                        }}{{ index < packageData.maintainers.length - 1 ? ", " : "" }}
                    </span>
                </div>

                <div class="small">
                    <a
                        v-if="packageData.homepage"
                        :href="packageData.homepage"
                        target="_blank"
                        rel="noopener"
                        class="mr-3">
                        Homepage <i class="fa fa-external-link-alt fa-sm"></i>
                    </a>
                    <a v-if="packageData.repository" :href="packageData.repository" target="_blank" rel="noopener">
                        Repository <i class="fa fa-external-link-alt fa-sm"></i>
                    </a>
                </div>
            </div>

            <div class="ml-3">
                <b-button
                    v-if="!isInstalled"
                    variant="primary"
                    size="sm"
                    :disabled="isLoading"
                    @click="$emit('install', packageData)">
                    <b-spinner v-if="isLoading" small></b-spinner>
                    <i v-else class="fa fa-download mr-1"></i>
                    Install
                </b-button>

                <b-button v-else variant="outline-success" size="sm" disabled>
                    <i class="fa fa-check mr-1"></i>
                    Installed
                </b-button>
            </div>
        </div>
    </b-card>
</template>

<script>
export default {
    name: "AvailableVisualizationCard",

    props: {
        packageData: {
            type: Object,
            required: true,
        },
        installedVisualizations: {
            type: Array,
            default: () => [],
        },
        loadingActions: {
            type: Set,
            default: () => new Set(),
        },
    },

    computed: {
        isInstalled() {
            return this.installedVisualizations.some((viz) => viz.package === this.visualization.name);
        },

        isLoading() {
            return this.loadingActions.has(`install-${this.visualization.name}`);
        },
    },

    methods: {
        formatDate(dateString) {
            try {
                return new Date(dateString).toLocaleDateString();
            } catch {
                return dateString;
            }
        },
    },
};
</script>

<style scoped>
.available-visualization-card {
    transition: box-shadow 0.15s ease-in-out;
}

.available-visualization-card:hover {
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

.badge {
    font-size: 0.75em;
}
</style>
