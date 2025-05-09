<script setup lang="ts">
import { BLink, BTab, BTabs, BCollapse } from "bootstrap-vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronUp, faChevronDown, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { STATES } from "@/components/History/Content/model/states";
import { useDatasetStore } from "@/stores/datasetStore";

import Heading from "../Common/Heading.vue";
import DatasetError from "../DatasetInformation/DatasetError.vue";
import DatasetAttributes from "@/components/DatasetInformation/DatasetAttributes.vue";
import DatasetDetails from "@/components/DatasetInformation/DatasetDetails.vue";
import VisualizationsList from "@/components/Visualizations/Index.vue";

library.add(faChevronUp, faChevronDown, faSpinner);

const datasetStore = useDatasetStore();
const router = useRouter();
const headerState = ref<"open" | "closed">("open");

const props = defineProps({
    datasetId: {
        type: String,
        required: true,
    },
    tab: {
        type: String,
        default: "preview",
    },
});

type TabNames = "preview" | "details" | "visualize" | "edit" | "error";

const TABS = {
    PREVIEW: 0,
    DETAILS: 1,
    VISUALIZE: 2,
    EDIT: 3,
    ERROR: 4,
} as const;

type TabIndex = (typeof TABS)[keyof typeof TABS];

const tabIndexToName: Record<number, TabNames> = {
    [TABS.PREVIEW]: "preview",
    [TABS.DETAILS]: "details",
    [TABS.VISUALIZE]: "visualize",
    [TABS.EDIT]: "edit",
    [TABS.ERROR]: "error",
};

const tabNameToIndex: Record<TabNames, number> = {
    preview: TABS.PREVIEW,
    details: TABS.DETAILS,
    visualize: TABS.VISUALIZE,
    edit: TABS.EDIT,
    error: TABS.ERROR,
};

const activeTab = ref<TabIndex>(TABS.PREVIEW);

const dataset = computed(() => datasetStore.getDataset(props.datasetId));
const isLoading = computed(() => datasetStore.isLoadingDataset(props.datasetId));
const displayUrl = computed(() => `/datasets/${props.datasetId}/display/?preview=true`);
const showError = computed(
    () => dataset.value && (dataset.value.state === "error" || dataset.value.state === "failed_metadata")
);

const contentState = computed(() => {
    return dataset.value && STATES[dataset.value.state] ? STATES[dataset.value.state] : null;
});

const stateText = computed(() => dataset.value && dataset.value.state || "");

const hasStateIcon = computed(() => {
    return contentState.value && contentState.value.icon;
});

function toggleHeader() {
    headerState.value = headerState.value === "open" ? "closed" : "open";
}

function onTabChange(tabIndex: number) {
    if (!(tabIndex in tabIndexToName)) {
        console.error("Invalid tab index received:", tabIndex);
        return;
    }

    const tabName = tabIndexToName[tabIndex];

    if (tabIndex === TABS.ERROR && !showError.value) {
        return;
    }

    const basePath = `/datasets/${props.datasetId}`;
    const targetPath = tabIndex === TABS.PREVIEW ? basePath : `${basePath}/${tabName}`;

    // Always push the navigation request; vue-router handles duplicates if the path is identical.
    router.push(targetPath);
}

// Set the active tab based on the current route
function setActiveTabFromProp() {
    const currentTabName = props.tab as string; // Use the prop value
    let targetIndex = tabNameToIndex[currentTabName as TabNames] as TabIndex;

    if (targetIndex === undefined) {
        targetIndex = TABS.PREVIEW;
        if (currentTabName !== "preview") {
            const previewPath = `/datasets/${props.datasetId}`;
            router.replace(previewPath);
            return;
        }
    } else if (targetIndex === TABS.ERROR && !showError.value) {
        targetIndex = TABS.PREVIEW;
        if (currentTabName === "error") {
            const previewPath = `/datasets/${props.datasetId}`;
            router.replace(previewPath);
            return;
        }
    }

    if (activeTab.value !== targetIndex) {
        activeTab.value = targetIndex;
    }
}

// Watch the 'tab' prop instead of the route path
watch(() => props.tab, setActiveTabFromProp, { immediate: true });
</script>
<template>
    <div v-if="dataset && !isLoading" class="dataset-view d-flex flex-column">
        <header class="dataset-header flex-shrink-0">
            <Heading
                h1
                separator
                :collapse="headerState"
                class="dataset-name"
                @click="toggleHeader">
                <div class="item-identifier">
                    <span class="hid-box">{{ dataset.hid }}:</span>
                    <span class="dataset-title">{{ dataset.name }}</span>
                    <span v-if="contentState" class="state-pill ml-2" :class="`state-${dataset.state}`">
                        <span v-if="hasStateIcon" class="state-icon mr-1">
                            <FontAwesomeIcon
                                fixed-width
                                :icon="contentState.icon"
                                :spin="contentState.spin" />
                        </span>
                        {{ stateText }}
                    </span>
                </div>
            </Heading>

            <div v-if="headerState === 'open'" class="header-details">
                <div v-if="dataset.misc_blurb" class="blurb">
                    <span class="value">{{ dataset.misc_blurb }}</span>
                </div>
                <span v-if="dataset.file_ext" class="datatype">
                    <span v-localize class="prompt">format</span>
                    <span class="value font-weight-bold">{{ dataset.file_ext }}</span>
                </span>
                <span v-if="dataset.genome_build" class="dbkey">
                    <span v-localize class="prompt">database</span>
                    <BLink class="value font-weight-bold" data-label="Database/Build" @click="onTabChange(TABS.EDIT)">{{
                        dataset.genome_build
                    }}</BLink>
                </span>
                <div v-if="dataset.misc_info" class="info">
                    <span class="value">{{ dataset.misc_info }}</span>
                </div>
            </div>
        </header>

        <!-- Tab container - make it grow to fill remaining space and handle overflow -->
        <div class="dataset-tabs-container flex-grow-1 overflow-hidden">
            <!-- Make BTabs fill its container and use flex column layout internally -->
            <BTabs pills card lazy class="h-100 d-flex flex-column" :value="activeTab" @input="onTabChange">
                <BTab title="Preview" class="iframe-card">
                    <!-- Iframe for dataset preview -->
                    <iframe
                        :src="displayUrl"
                        title="galaxy dataset display frame"
                        class="dataset-preview-iframe"
                        frameborder="0"></iframe>
                </BTab>
                <BTab title="Details">
                    <DatasetDetails :dataset-id="datasetId" />
                </BTab>
                <BTab title="Visualize">
                    <VisualizationsList :dataset-id="datasetId" />
                </BTab>
                <BTab title="Edit">
                    <DatasetAttributes :dataset-id="datasetId" />
                </BTab>
                <BTab v-if="showError" title="Error Report">
                    <DatasetError :dataset-id="datasetId" />
                </BTab>
            </BTabs>
        </div>
    </div>
    <!-- Loading state indicator -->
    <div v-else class="loading-message">Loading dataset details...</div>
</template>

<style scoped>
.dataset-view {
    height: 100%;
}

.dataset-header {
    margin-bottom: 1rem;
}

.item-identifier {
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    flex-wrap: wrap;
}

.dataset-name {
    margin-bottom: 0;
}

.hid-box {
    font-weight: bold;
    margin-right: 0.5rem;
    white-space: nowrap;
}

.dataset-title {
    white-space: normal;
    word-break: break-word;
}

.state-icon {
    display: inline-flex;
    align-items: center;
}

.state-pill {
    display: inline-flex;
    align-items: center;
    padding: 0.15rem 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.85rem;
    white-space: nowrap;
}

.state-running, .state-upload {
    background-color: #cff4fc;
    color: #055160;
}

.state-queued, .state-new {
    background-color: #e2e3e5;
    color: #41464b;
}

.state-ok {
    background-color: #d1e7dd;
    color: #0f5132;
}

.state-error, .state-failed_metadata {
    background-color: #f8d7da;
    color: #842029;
}

.header-details {
    margin-top: 0.5rem;
    padding-left: 1rem;
}

.dataset-tabs-container {
    min-height: 0; /* fix for flex-grow behavior in some contexts */
}

.dataset-tabs-container :deep(.nav-tabs) {
    flex-shrink: 0;
}

.dataset-tabs-container :deep(.tab-content) {
    flex-grow: 1;
    min-height: 0;
}

.dataset-tabs-container :deep(.tab-pane) {
    height: 100%;
    width: 100%;
    display: flex;
    flex-direction: column;
}

.dataset-tabs-container :deep(.iframe-card) {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    /* Remove padding for the iframe tab, we add back for others */
    padding: 0;
    overflow: hidden;
}

.dataset-preview-iframe {
    flex-grow: 1;
    border: none;
    width: 100%;
    height: 100%;
}

.loading-message {
    padding: 2rem;
    text-align: center;
    font-style: italic;
}
</style>
