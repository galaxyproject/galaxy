<template>
    <b-card class="visualization-card">
        <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
                <div class="d-flex align-items-center mb-2">
                    <h5 class="mb-0 mr-2">{{ visualization.id }}</h5>
                    <b-badge :variant="visualization.enabled ? 'success' : 'secondary'" class="mr-2">
                        {{ visualization.enabled ? "Enabled" : "Disabled" }}
                    </b-badge>
                    <b-badge
                        v-if="!visualization.installed"
                        variant="warning"
                        class="mr-2"
                        title="Registered in config but package files are missing from disk">
                        Missing Files
                    </b-badge>
                    <b-badge
                        v-if="visualization.installed"
                        :variant="isStaged ? 'info' : 'warning'"
                        class="mr-2"
                        :title="
                            isStaged
                                ? 'Assets are in Galaxy\'s serving directory'
                                : 'Assets need to be staged before users can access this visualization'
                        ">
                        {{ isStaged ? "Staged" : "Not Staged" }}
                    </b-badge>
                </div>

                <div class="text-muted mb-2">
                    <div class="d-flex flex-wrap">
                        <span class="mr-3"> <strong>Package:</strong> {{ visualization.package }} </span>
                        <span class="mr-3"> <strong>Version:</strong> {{ visualization.version }} </span>
                        <span v-if="visualization.size" class="mr-3">
                            <strong>Size:</strong> {{ bytesToString(visualization.size, true, 1) }}
                        </span>
                    </div>
                </div>

                <div v-if="meta?.description" class="mb-2">
                    <p class="text-muted mb-1">{{ meta.description }}</p>
                </div>

                <div v-if="meta" class="small text-muted">
                    <div class="d-flex flex-wrap">
                        <span v-if="meta.author" class="mr-3"> <strong>Author:</strong> {{ meta.author }} </span>
                        <span v-if="meta.license" class="mr-3"> <strong>License:</strong> {{ meta.license }} </span>
                        <span v-if="meta.homepage" class="mr-3">
                            <a :href="meta.homepage" target="_blank" rel="noopener">
                                Homepage
                                <FontAwesomeIcon :icon="faExternalLinkAlt" size="sm" />
                            </a>
                        </span>
                    </div>
                </div>

                <div v-if="meta?.dependencies && Object.keys(meta.dependencies).length > 0" class="mt-2">
                    <b-button v-b-toggle="`deps-${visualization.id}`" variant="link" size="sm" class="p-0 text-info">
                        <FontAwesomeIcon :icon="faCaretRight" fixed-width />
                        Dependencies ({{ Object.keys(meta.dependencies).length }})
                    </b-button>
                    <b-collapse :id="`deps-${visualization.id}`" class="mt-2">
                        <div class="small">
                            <div v-for="(version, dep) in meta.dependencies" :key="`dep-${dep}`" class="mb-1">
                                <code>{{ dep }}@{{ version }}</code>
                            </div>
                        </div>
                    </b-collapse>
                </div>
            </div>

            <div class="ml-3">
                <b-dropdown variant="outline-secondary" size="sm" right text="Actions" :disabled="isLoading">
                    <b-dropdown-item :disabled="isLoading" @click="emit('toggle', visualization)">
                        <FontAwesomeIcon :icon="visualization.enabled ? faEyeSlash : faEye" fixed-width />
                        {{ visualization.enabled ? "Disable" : "Enable" }}
                    </b-dropdown-item>

                    <b-dropdown-item v-if="visualization.installed" :disabled="isLoading" @click="openUpdateModal">
                        <FontAwesomeIcon :icon="faArrowUp" fixed-width />
                        Update
                    </b-dropdown-item>

                    <b-dropdown-item :disabled="isLoading" @click="emit('stage', visualization)">
                        <FontAwesomeIcon :icon="faUpload" fixed-width />
                        Stage Assets
                    </b-dropdown-item>

                    <b-dropdown-item
                        v-if="visualization.installed"
                        :disabled="isLoading"
                        variant="danger"
                        @click="emit('uninstall', visualization)">
                        <FontAwesomeIcon :icon="faTrash" fixed-width />
                        Uninstall
                    </b-dropdown-item>

                    <b-dropdown-divider v-if="visualization.installed" />

                    <b-dropdown-item :disabled="isLoading" @click="showDetails = !showDetails">
                        <FontAwesomeIcon :icon="faInfoCircle" fixed-width />
                        {{ showDetails ? "Hide Details" : "Show Details" }}
                    </b-dropdown-item>
                </b-dropdown>
            </div>
        </div>

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
                        <div v-if="meta" class="mb-2">
                            <strong>Package Metadata:</strong>
                            <br />
                            <pre class="small bg-light p-2 rounded">{{ JSON.stringify(meta, null, 2) }}</pre>
                        </div>
                    </div>
                </div>
            </div>
        </b-collapse>

        <b-modal
            v-model="showUpdateModal"
            title="Update Visualization"
            :ok-disabled="!updateVersion || updating"
            ok-title="Update"
            @ok="handleUpdate">
            <div v-if="updating" class="text-center">
                <b-spinner label="Updating..." />
                <p class="mt-2">Updating visualization package...</p>
            </div>

            <div v-else>
                <p>
                    Update <strong>{{ visualization.id }}</strong> ({{ visualization.package }})
                </p>

                <b-form-group label="Version:" label-for="version-input">
                    <b-form-select v-if="availableVersions.length > 0" id="version-input" v-model="updateVersion">
                        <b-form-select-option :value="''" disabled>Select a version...</b-form-select-option>
                        <b-form-select-option
                            v-for="v in availableVersions"
                            :key="v"
                            :value="v"
                            :disabled="v === visualization.version">
                            {{ v }}{{ v === visualization.version ? " (current)" : "" }}
                        </b-form-select-option>
                    </b-form-select>
                    <div v-else-if="loadingVersions" class="text-muted small">
                        <b-spinner small class="mr-1" />
                        Loading available versions...
                    </div>
                    <b-form-input v-else id="version-input" v-model="updateVersion" placeholder="e.g., 1.2.3" />
                    <b-form-text> Current version: {{ visualization.version }} </b-form-text>
                </b-form-group>
            </div>
        </b-modal>
    </b-card>
</template>

<script setup lang="ts">
import {
    faArrowUp,
    faCaretRight,
    faExternalLinkAlt,
    faEye,
    faEyeSlash,
    faInfoCircle,
    faTrash,
    faUpload,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import { bytesToString } from "@/utils/utils";

import type { Visualization } from "./services";
import { getPackageVersions } from "./services";

interface PackageMetadata {
    description?: string;
    author?: string;
    license?: string;
    homepage?: string;
    dependencies?: Record<string, string>;
    [key: string]: unknown;
}

interface Props {
    visualization: Visualization;
    loadingActions?: Record<string, boolean>;
    stagedNames?: string[];
}

const props = withDefaults(defineProps<Props>(), {
    loadingActions: () => ({}),
    stagedNames: () => [] as string[],
});

const meta = computed(() => (props.visualization.metadata as PackageMetadata | null) ?? null);

const emit = defineEmits<{
    (e: "toggle", visualization: Visualization): void;
    (e: "update", visualization: Visualization, version: string): void;
    (e: "uninstall", visualization: Visualization): void;
    (e: "stage", visualization: Visualization): void;
    (e: "refresh"): void;
}>();

const showDetails = ref(false);
const showUpdateModal = ref(false);
const updateVersion = ref("");
const updating = ref(false);
const availableVersions = ref<string[]>([]);
const loadingVersions = ref(false);

const isLoading = computed(() => {
    return (
        !!props.loadingActions[`toggle-${props.visualization.id}`] ||
        !!props.loadingActions[`update-${props.visualization.id}`] ||
        !!props.loadingActions[`uninstall-${props.visualization.id}`] ||
        !!props.loadingActions[`stage-${props.visualization.id}`] ||
        updating.value
    );
});

const isStaged = computed(() => props.stagedNames.includes(props.visualization.id));

watch(showUpdateModal, (isShown) => {
    if (!isShown) {
        updateVersion.value = "";
        updating.value = false;
        availableVersions.value = [];
    }
});

async function openUpdateModal() {
    showUpdateModal.value = true;
    loadingVersions.value = true;
    try {
        const result = await getPackageVersions(props.visualization.package);
        availableVersions.value = result.versions ?? [];
    } catch {
        // Fall back to manual text input if version fetch fails
        availableVersions.value = [];
    } finally {
        loadingVersions.value = false;
    }
}

function handleUpdate() {
    if (!updateVersion.value) {
        return;
    }
    emit("update", props.visualization, updateVersion.value);
    showUpdateModal.value = false;
    updateVersion.value = "";
}
</script>

<style scoped>
.visualization-card {
    transition: box-shadow 0.15s ease-in-out;
}

.visualization-card:hover {
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

pre {
    font-size: 0.75rem;
    max-height: 200px;
    overflow-y: auto;
}
</style>
