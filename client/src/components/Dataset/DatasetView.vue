<script setup lang="ts">
import { faBug, faChartBar, faEye, faFileAlt, faInfoCircle, faPen } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink, BNav, BNavItem } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { usePersistentToggle } from "@/composables/persistentToggle";
import { useDatasetStore } from "@/stores/datasetStore";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import { useDatatypeStore } from "@/stores/datatypeStore";
import { withPrefix } from "@/utils/redirect";
import { bytesToString } from "@/utils/utils";

import DatasetError from "../DatasetInformation/DatasetError.vue";
import LoadingSpan from "../LoadingSpan.vue";
import DatasetAsImage from "./DatasetAsImage/DatasetAsImage.vue";
import DatasetDisplay from "./DatasetDisplay.vue";
import DatasetState from "./DatasetState.vue";
import Heading from "@/components/Common/Heading.vue";
import DatasetAttributes from "@/components/DatasetInformation/DatasetAttributes.vue";
import DatasetDetails from "@/components/DatasetInformation/DatasetDetails.vue";
import VisualizationsList from "@/components/Visualizations/Index.vue";
import VisualizationFrame from "@/components/Visualizations/VisualizationFrame.vue";

const datasetStore = useDatasetStore();
const datatypeStore = useDatatypeStore();
const datatypesMapperStore = useDatatypesMapperStore();
const { toggled: headerCollapsed, toggle: toggleHeaderCollapse } = usePersistentToggle("dataset-header-collapsed");

interface Props {
    datasetId: string;
    tab?: "details" | "edit" | "error" | "preview" | "raw" | "visualize";
    displayOnly?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    tab: "preview",
    displayOnly: false,
});

const iframeLoading = ref(true);

const dataset = computed(() => datasetStore.getDataset(props.datasetId));
const headerState = computed(() => (headerCollapsed.value ? "closed" : "open"));

// Track datatype loading state
const isDatatypeLoading = ref(false);

// Consolidated loading state
const isLoading = computed(() => {
    return datasetStore.isLoadingDataset(props.datasetId) || isDatatypeLoading.value || datatypesMapperStore.loading;
});

const showError = computed(
    () => dataset.value && (dataset.value.state === "error" || dataset.value.state === "failed_metadata"),
);
const isAutoDownloadType = computed(
    () => dataset.value && datatypeStore.isDatatypeAutoDownload(dataset.value.file_ext),
);
const downloadUrl = computed(() => withPrefix(`/datasets/${props.datasetId}/display`));
const preferredVisualization = computed(
    () => dataset.value && datatypeStore.getPreferredVisualization(dataset.value.file_ext),
);
const isBinaryDataset = computed(() => {
    if (!dataset.value?.file_ext || !datatypesMapperStore.datatypesMapper) {
        return false;
    }
    return datatypesMapperStore.datatypesMapper.isSubTypeOfAny(dataset.value.file_ext, ["galaxy.datatypes.binary"]);
});

const isImageDataset = computed(() => {
    if (!dataset.value?.file_ext || !datatypesMapperStore.datatypesMapper) {
        return false;
    }
    return datatypesMapperStore.datatypesMapper.isSubTypeOfAny(dataset.value.file_ext, [
        "galaxy.datatypes.images.Image",
    ]);
});

const isPdfDataset = computed(() => {
    return dataset.value?.file_ext === "pdf";
});

// Watch for changes to the dataset to fetch datatype info
watch(
    () => dataset.value?.file_ext,
    async () => {
        if (dataset.value && dataset.value.file_ext) {
            isDatatypeLoading.value = true;
            await Promise.all([
                datatypeStore.fetchDatatypeDetails(dataset.value.file_ext),
                datatypesMapperStore.createMapper(),
            ]);
            isDatatypeLoading.value = false;
        }
    },
    { immediate: true },
);
</script>

<template>
    <LoadingSpan v-if="isLoading || !dataset" message="Loading dataset details" />
    <div v-else class="dataset-view d-flex flex-column h-100">
        <header v-if="!displayOnly" :key="`dataset-header-${dataset.id}`" class="dataset-header flex-shrink-0">
            <div class="d-flex">
                <Heading
                    h1
                    separator
                    inline
                    size="lg"
                    class="flex-grow-1"
                    :collapse="headerState"
                    @click="toggleHeaderCollapse">
                    <div class="dataset-header-content">
                        <div class="dataset-title-row">
                            <span class="dataset-hid">{{ dataset?.hid }}:</span>
                            <span class="dataset-name font-weight-bold">{{ dataset?.name }}</span>
                        </div>
                        <span class="dataset-state-header">
                            <DatasetState :dataset-id="datasetId" />
                        </span>
                    </div>
                </Heading>
            </div>
            <transition v-if="dataset" name="header">
                <div v-show="headerState === 'open'" class="header-details">
                    <div v-if="dataset.misc_blurb" class="blurb">
                        <span class="value">{{ dataset.misc_blurb }}</span>
                    </div>
                    <span v-if="dataset.file_ext" class="datatype">
                        <span v-localize class="prompt">format</span>
                        <span class="value font-weight-bold">{{ dataset.file_ext }}</span>
                    </span>
                    <span v-if="dataset.genome_build" class="dbkey">
                        <span v-localize class="prompt">database</span>
                        <BLink
                            class="value font-weight-bold"
                            data-label="Database/Build"
                            :to="`/datasets/${datasetId}/edit`">
                            {{ dataset.genome_build }}
                        </BLink>
                    </span>
                    <span v-if="dataset.file_size" class="filesize">
                        <span v-localize class="prompt">size</span>
                        <span class="value font-weight-bold" v-html="bytesToString(dataset.file_size, false)" />
                    </span>
                </div>
            </transition>
        </header>
        <BNav v-if="!displayOnly" pills class="my-2 p-2 bg-light border-bottom">
            <BNavItem
                title="View a preview of the dataset contents"
                :active="tab === 'preview'"
                :to="`/datasets/${datasetId}/preview`">
                <FontAwesomeIcon :icon="faEye" class="mr-1" /> Preview
            </BNavItem>
            <BNavItem
                v-if="preferredVisualization"
                title="View raw dataset contents"
                :active="tab === 'raw'"
                :to="`/datasets/${datasetId}/raw`">
                <FontAwesomeIcon :icon="faFileAlt" class="mr-1" /> Raw
            </BNavItem>
            <BNavItem
                v-if="!showError"
                title="Explore available visualizations for this dataset"
                :active="tab === 'visualize'"
                :to="`/datasets/${datasetId}/visualize`">
                <FontAwesomeIcon :icon="faChartBar" class="mr-1" /> Visualize
            </BNavItem>
            <BNavItem
                title="View detailed information about this dataset"
                :active="tab === 'details'"
                :to="`/datasets/${datasetId}/details`">
                <FontAwesomeIcon :icon="faInfoCircle" class="mr-1" /> Details
            </BNavItem>
            <BNavItem
                title="Edit dataset attributes and metadata"
                :active="tab === 'edit'"
                :to="`/datasets/${datasetId}/edit`">
                <FontAwesomeIcon :icon="faPen" class="mr-1" /> Edit
            </BNavItem>
            <BNavItem
                v-if="showError"
                title="View error information for this dataset"
                :active="tab === 'error'"
                :to="`/datasets/${datasetId}/error`">
                <FontAwesomeIcon :icon="faBug" class="mr-1" /> Error
            </BNavItem>
        </BNav>
        <div v-if="tab === 'preview'" class="h-100">
            <VisualizationFrame
                v-if="preferredVisualization"
                :dataset-id="datasetId"
                :visualization="preferredVisualization"
                @load="iframeLoading = false" />
            <div v-else-if="isAutoDownloadType && !isPdfDataset" class="auto-download-message p-4">
                <div class="alert alert-info">
                    <h4>Download Required</h4>
                    <p>This file type ({{ dataset.file_ext }}) will download automatically when accessed directly.</p>
                    <p>File size: <strong v-html="bytesToString(dataset.file_size || 0, false)" /></p>
                    <a :href="downloadUrl" class="btn btn-primary mt-2" download>
                        <FontAwesomeIcon :icon="faFileAlt" class="mr-1" /> Download File
                    </a>
                </div>
            </div>
            <DatasetAsImage
                v-else-if="isImageDataset && !isPdfDataset"
                :history-dataset-id="datasetId"
                :allow-size-toggle="true"
                class="p-3" />
            <DatasetDisplay v-else :dataset-id="datasetId" :is-binary="isBinaryDataset" @load="iframeLoading = false" />
        </div>
        <div v-else-if="tab === 'raw'" class="h-100">
            <div v-if="isAutoDownloadType && !isPdfDataset" class="auto-download-message p-4">
                <div class="alert alert-info">
                    <h4>Download Required</h4>
                    <p>This file type ({{ dataset.file_ext }}) will download automatically when accessed directly.</p>
                    <p>File size: <strong v-html="bytesToString(dataset.file_size || 0, false)" /></p>
                    <a :href="downloadUrl" class="btn btn-primary mt-2" download>
                        <FontAwesomeIcon :icon="faFileAlt" class="mr-1" /> Download File
                    </a>
                </div>
            </div>
            <DatasetDisplay v-else :dataset-id="datasetId" :is-binary="isBinaryDataset" @load="iframeLoading = false" />
        </div>
        <div v-else-if="tab === 'visualize'" class="tab-content-panel">
            <VisualizationsList :dataset-id="datasetId" />
        </div>
        <div v-else-if="tab === 'edit'" class="tab-content-panel mt-2">
            <DatasetAttributes :dataset-id="datasetId" />
        </div>
        <div v-else-if="tab === 'details'" class="tab-content-panel mt-2">
            <DatasetDetails :dataset-id="datasetId" />
        </div>
        <div v-else-if="tab === 'error'" class="tab-content-panel mt-2">
            <DatasetError :dataset-id="datasetId" />
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.header-details {
    padding-left: 1rem;
    max-height: 500px;
    opacity: 1;
    transition: all 0.25s ease;
    overflow: hidden;

    .datatype,
    .dbkey,
    .filesize {
        margin-right: 1rem;
    }

    .prompt {
        color: $text-muted;
        margin-right: 0.25rem;
    }

    .blurb {
        margin-bottom: 0.25rem;
    }
}

.header-enter, /* change to header-enter-from with Vue 3 */
.header-leave-to {
    max-height: 0;
    margin-top: 0;
    padding-top: 0;
    padding-bottom: 0;
    opacity: 0;
}

.dataset-header-content {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.5rem;
}

.dataset-title-row {
    display: flex;
    align-items: baseline;
    min-width: 0;
    flex: 1 1 auto;
}

.dataset-hid {
    white-space: nowrap;
    margin-right: 0.25rem;
}

.dataset-name {
    word-break: break-word;
    min-width: 0;
}

.dataset-state-header {
    font-size: $h5-font-size;
    flex: 0 0 auto;
    white-space: nowrap;
}

.tab-content-panel {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    overflow-y: auto;
    height: 100%;
}

.auto-download-message {
    display: flex;
    align-items: flex-start;
    justify-content: center;
    height: 100%;

    .alert {
        max-width: 600px;
        width: 100%;
    }
}
</style>
