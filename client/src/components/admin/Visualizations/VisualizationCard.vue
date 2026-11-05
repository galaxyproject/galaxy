<template>
    <BCard class="visualization-card">
        <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
                <div class="d-flex align-items-center mb-2">
                    <h5 class="mb-0 mr-2">{{ visualization.id }}</h5>
                    <BBadge :variant="visualization.enabled ? 'success' : 'secondary'" class="mr-2">
                        {{ visualization.enabled ? "Enabled" : "Disabled" }}
                    </BBadge>
                    <BBadge
                        v-if="!visualization.installed"
                        variant="warning"
                        class="mr-2"
                        title="Registered in config but package files are missing from disk">
                        Missing Files
                    </BBadge>
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
                        <span v-if="authorName" class="mr-3"> <strong>Author:</strong> {{ authorName }} </span>
                        <span v-if="meta.license" class="mr-3"> <strong>License:</strong> {{ meta.license }} </span>
                        <span v-if="homepageUrl" class="mr-3">
                            <a :href="homepageUrl" target="_blank" rel="noopener">
                                Homepage
                                <FontAwesomeIcon :icon="faExternalLinkAlt" size="sm" />
                            </a>
                        </span>
                    </div>
                </div>

                <div v-if="meta?.dependencies && Object.keys(meta.dependencies).length > 0" class="mt-2">
                    <GLink @click="showDependencies = !showDependencies">
                        <FontAwesomeIcon :icon="faCaretRight" fixed-width />
                        Dependencies ({{ Object.keys(meta.dependencies).length }})
                    </GLink>
                    <GCollapse v-model="showDependencies" class="mt-2">
                        <div class="small">
                            <div v-for="(version, dep) in meta.dependencies" :key="`dep-${dep}`" class="mb-1">
                                <code>{{ dep }}@{{ version }}</code>
                            </div>
                        </div>
                    </GCollapse>
                </div>
            </div>

            <div class="ml-3 flex-shrink-0">
                <GDropdown variant="outline-secondary" size="sm" right text="Actions" :disabled="isLoading">
                    <GDropdownItem :disabled="isLoading" @click="emit('toggle', visualization)">
                        <FontAwesomeIcon :icon="visualization.enabled ? faEyeSlash : faEye" fixed-width />
                        {{ visualization.enabled ? "Disable" : "Enable" }}
                    </GDropdownItem>

                    <GDropdownItem v-if="visualization.installed" :disabled="isLoading" @click="openUpdateModal">
                        <FontAwesomeIcon :icon="faArrowUp" fixed-width />
                        Update
                    </GDropdownItem>

                    <GDropdownItem :disabled="isLoading" variant="danger" @click="emit('uninstall', visualization)">
                        <FontAwesomeIcon :icon="faTrash" fixed-width />
                        Uninstall
                    </GDropdownItem>

                    <GDropdownDivider />

                    <GDropdownItem :disabled="isLoading" @click="showDetails = !showDetails">
                        <FontAwesomeIcon :icon="faInfoCircle" fixed-width />
                        {{ showDetails ? "Hide Details" : "Show Details" }}
                    </GDropdownItem>
                </GDropdown>
            </div>
        </div>

        <GCollapse v-model="showDetails" class="mt-3">
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
        </GCollapse>

        <GModal
            v-model:show="showUpdateModal"
            title="Update Visualization"
            confirm
            :ok-disabled="!updateVersion || updating"
            ok-text="Update"
            @ok="handleUpdate">
            <div v-if="updating" class="text-center">
                <LoadingSpan message="Updating visualization package" />
            </div>

            <div v-else>
                <p>
                    Update <strong>{{ visualization.id }}</strong> ({{ visualization.package }})
                </p>

                <GFormLabel title="Version:" :description="`Current version: ${visualization.version}`">
                    <GSelect v-if="availableVersions.length > 0" v-model="updateVersion" :options="versionOptions" />
                    <LoadingSpan v-else-if="loadingVersions" message="Loading available versions" />
                    <GFormInput v-else v-model="updateVersion" placeholder="e.g., 1.2.3" />
                </GFormLabel>
            </div>
        </GModal>
    </BCard>
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
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge, BCard } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { bytesToString } from "@/utils/utils";

import { externalUrl } from "./links";
import type { Visualization } from "./services";
import { getPackageVersions } from "./services";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GFormLabel from "@/components/BaseComponents/Form/GFormLabel.vue";
import GCollapse from "@/components/BaseComponents/GCollapse.vue";
import GDropdown from "@/components/BaseComponents/GDropdown.vue";
import GDropdownDivider from "@/components/BaseComponents/GDropdownDivider.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import GSelect from "@/components/BaseComponents/GSelect.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface PackageMetadata {
    description?: string;
    author?: string | { name?: string };
    license?: string;
    homepage?: string;
    dependencies?: Record<string, string>;
    [key: string]: unknown;
}

interface Props {
    visualization: Visualization;
    loadingActions?: Record<string, boolean>;
}

const props = withDefaults(defineProps<Props>(), {
    loadingActions: () => ({}),
});

const meta = computed(() => (props.visualization.metadata as PackageMetadata | null) ?? null);
const homepageUrl = computed(() => externalUrl(meta.value?.homepage));
// npm allows either "Name <email>" or {name, email, url}
const authorName = computed(() => {
    const author = meta.value?.author;
    return typeof author === "string" ? author : author?.name;
});

const emit = defineEmits<{
    (e: "toggle", visualization: Visualization): void;
    (e: "update", visualization: Visualization, version: string): void;
    (e: "uninstall", visualization: Visualization): void;
    (e: "refresh"): void;
}>();

const showDetails = ref(false);
const showDependencies = ref(false);
const showUpdateModal = ref(false);
const updateVersion = ref("");
const updating = ref(false);
const availableVersions = ref<string[]>([]);
const loadingVersions = ref(false);

const versionOptions = computed(() => [
    { text: "Select a version...", value: "", disabled: true },
    ...availableVersions.value.map((version) => ({
        text: version === props.visualization.version ? `${version} (current)` : version,
        value: version,
        disabled: version === props.visualization.version,
    })),
]);

const isLoading = computed(() => {
    return (
        !!props.loadingActions[`toggle-${props.visualization.id}`] ||
        !!props.loadingActions[`update-${props.visualization.id}`] ||
        !!props.loadingActions[`uninstall-${props.visualization.id}`] ||
        updating.value
    );
});

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
