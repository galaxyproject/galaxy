<template>
    <BCard class="available-visualization-card">
        <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
                <div class="d-flex align-items-center mb-2">
                    <h5 class="mb-0 mr-2">{{ packageData.name }}</h5>
                    <BBadge variant="info" class="mr-2">v{{ packageData.version }}</BBadge>
                    <BBadge v-if="isInstalled" variant="success">Installed</BBadge>
                </div>

                <p v-if="packageData.description" class="text-muted mb-2">
                    {{ packageData.description }}
                </p>

                <div class="small text-muted mb-2">
                    <div class="d-flex flex-wrap">
                        <span v-if="packageData.keywords?.length" class="mr-3">
                            <strong>Keywords:</strong> {{ packageData.keywords.join(", ") }}
                        </span>
                        <span v-if="packageData.date" class="mr-3">
                            <strong>Last Updated:</strong> {{ formatDate(packageData.date) }}
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
                        v-if="packageData.links?.homepage"
                        :href="String(packageData.links.homepage)"
                        target="_blank"
                        rel="noopener"
                        class="mr-3">
                        Homepage <FontAwesomeIcon :icon="faExternalLinkAlt" size="sm" />
                    </a>
                    <a
                        v-if="packageData.links?.repository"
                        :href="String(packageData.links.repository)"
                        target="_blank"
                        rel="noopener">
                        Repository <FontAwesomeIcon :icon="faExternalLinkAlt" size="sm" />
                    </a>
                </div>
            </div>

            <div class="ml-3">
                <BButton
                    v-if="!isInstalled"
                    variant="primary"
                    size="sm"
                    :disabled="isLoading"
                    @click="emit('install', packageData)">
                    <BSpinner v-if="isLoading" small />
                    <FontAwesomeIcon v-else :icon="faDownload" class="mr-1" />
                    Install
                </BButton>

                <BButton v-else variant="outline-success" size="sm" disabled>
                    <FontAwesomeIcon :icon="faCheck" class="mr-1" />
                    Installed
                </BButton>
            </div>
        </div>
    </BCard>
</template>

<script setup lang="ts">
import { faCheck, faDownload, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge, BButton, BCard, BSpinner } from "bootstrap-vue";
import { computed } from "vue";

import type { AvailableVisualization, Visualization } from "./services";

interface Props {
    packageData: AvailableVisualization;
    installedPackages?: Visualization[];
    loadingActions?: Record<string, boolean>;
}

const props = withDefaults(defineProps<Props>(), {
    installedPackages: () => [],
    loadingActions: () => ({}),
});

const emit = defineEmits<{
    (e: "install", packageData: AvailableVisualization): void;
}>();

const isInstalled = computed(() => {
    return props.installedPackages.some((viz) => viz.package === props.packageData.name);
});

const isLoading = computed(() => {
    return !!props.loadingActions[`install-${props.packageData.name}`];
});

function formatDate(dateString: string) {
    try {
        return new Date(dateString).toLocaleDateString();
    } catch {
        return dateString;
    }
}
</script>

<style scoped>
.available-visualization-card {
    transition: box-shadow 0.15s ease-in-out;
}

.available-visualization-card:hover {
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}
</style>
