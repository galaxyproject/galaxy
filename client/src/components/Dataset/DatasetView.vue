<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BLink, BTab, BTabs } from "bootstrap-vue";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { STATES } from "@/components/History/Content/model/states";
import { usePersistentToggle } from "@/composables/persistentToggle";
import { useDatasetStore } from "@/stores/datasetStore";

import Heading from "../Common/Heading.vue";
import DatasetError from "../DatasetInformation/DatasetError.vue";
import LoadingSpan from "../LoadingSpan.vue";
import DatasetAttributes from "@/components/DatasetInformation/DatasetAttributes.vue";
import DatasetDetails from "@/components/DatasetInformation/DatasetDetails.vue";
import VisualizationsList from "@/components/Visualizations/Index.vue";

library.add(faChevronUp, faChevronDown);

const datasetStore = useDatasetStore();
const router = useRouter();
const iframeLoading = ref(true);

// Use persistent toggle for header state
const { toggled: headerCollapsed, toggle: toggleHeaderCollapse } = usePersistentToggle("dataset-header-collapsed");
const headerState = computed(() => (headerCollapsed.value ? "closed" : "open"));

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

const TABS = {
    PREVIEW: "preview",
    VISUALIZE: "visualize",
    DETAILS: "details",
    EDIT: "edit",
    ERROR: "error",
} as const;

type TabName = (typeof TABS)[keyof typeof TABS];
const TAB_VALUES = Object.values(TABS) as TabName[];

const activeTab = ref<TabName>(TABS.PREVIEW);

const dataset = computed(() => datasetStore.getDataset(props.datasetId));
const isLoading = computed(() => datasetStore.isLoadingDataset(props.datasetId));
const displayUrl = computed(() => `/datasets/${props.datasetId}/display/?preview=true`);
const showError = computed(
    () => dataset.value && (dataset.value.state === "error" || dataset.value.state === "failed_metadata")
);

const contentState = computed(() => {
    return dataset.value && STATES[dataset.value.state] ? STATES[dataset.value.state] : null;
});

const stateText = computed(() => (dataset.value && dataset.value.state) || "");

const hasStateIcon = computed(() => {
    return contentState.value && contentState.value.icon;
});

function toggleHeader() {
    toggleHeaderCollapse();
}

function onTabChange(tabName: TabName) {
    if (!TAB_VALUES.includes(tabName)) {
        console.error("Invalid tab name received:", tabName);
        return;
    }

    if (tabName === TABS.ERROR && !showError.value) {
        return;
    }

    if (tabName === TABS.PREVIEW) {
        iframeLoading.value = true;
    }

    const basePath = `/datasets/${props.datasetId}`;
    const targetPath = tabName === TABS.PREVIEW ? basePath : `${basePath}/${tabName}`;

    router.push(targetPath);
}

function setActiveTabFromProp() {
    const currentTabName = props.tab as string;

    if (!TAB_VALUES.includes(currentTabName as TabName)) {
        if (currentTabName !== TABS.PREVIEW) {
            const previewPath = `/datasets/${props.datasetId}`;
            router.replace(previewPath);
        }
        activeTab.value = TABS.PREVIEW;
        return;
    }

    if (currentTabName === TABS.ERROR && !showError.value) {
        if (currentTabName === TABS.ERROR) {
            const previewPath = `/datasets/${props.datasetId}`;
            router.replace(previewPath);
        }
        activeTab.value = TABS.PREVIEW;
        return;
    }

    if (activeTab.value !== currentTabName) {
        activeTab.value = currentTabName as TabName;
    }
}

// Watch the 'tab' prop instead of the route path
watch(() => props.tab, setActiveTabFromProp, { immediate: true });

// Reset iframe loading when datasetId changes
watch(
    () => props.datasetId,
    () => {
        if (activeTab.value === TABS.PREVIEW) {
            iframeLoading.value = true;
        }
    }
);
</script>
<template>
    <div v-if="dataset && !isLoading" class="dataset-view d-flex flex-column">
        <header :key="`dataset-header-${dataset.id}`" class="dataset-header flex-shrink-0">
            <Heading h1 separator :collapse="headerState" class="dataset-name" @click="toggleHeader">
                <div class="item-identifier">
                    <span class="hid-box">{{ dataset.hid }}:</span>
                    <span class="dataset-title">{{ dataset.name }}</span>
                    <span v-if="contentState" class="state-pill ml-2" :class="`state-${dataset.state}`">
                        <span v-if="hasStateIcon" class="state-icon mr-1">
                            <FontAwesomeIcon fixed-width :icon="contentState.icon" :spin="contentState.spin" />
                        </span>
                        {{ stateText }}
                    </span>
                </div>
            </Heading>

            <transition name="header">
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
                        <BLink
                            class="value font-weight-bold"
                            data-label="Database/Build"
                            @click="onTabChange(TABS.EDIT)"
                            >{{ dataset.genome_build }}</BLink
                        >
                    </span>
                    <div v-if="dataset.misc_info" class="info">
                        <span class="value">{{ dataset.misc_info }}</span>
                    </div>
                </div>
            </transition>
        </header>

        <!-- Tab container - make it grow to fill remaining space and handle overflow -->
        <div class="dataset-tabs-container flex-grow-1 overflow-hidden">
            <BTabs
                :key="`tabs-${datasetId}`"
                pills
                card
                lazy
                class="h-100 d-flex flex-column"
                :value="TAB_VALUES.indexOf(activeTab)"
                @input="(tabIndex) => onTabChange(TAB_VALUES[tabIndex])">
                <BTab title="Preview" class="iframe-card">
                    <div class="preview-container position-relative h-100">
                        <!-- Loading indicator for iframe -->
                        <div v-if="iframeLoading" class="iframe-loading">
                            <LoadingSpan message="Loading preview" />
                        </div>

                        <!-- Iframe for dataset preview -->
                        <iframe
                            :src="displayUrl"
                            title="galaxy dataset display frame"
                            class="dataset-preview-iframe"
                            frameborder="0"
                            @load="iframeLoading = false"></iframe>
                    </div>
                </BTab>
                <BTab title="Visualize">
                    <VisualizationsList :dataset-id="datasetId" />
                </BTab>
                <BTab title="Details">
                    <DatasetDetails :dataset-id="datasetId" />
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
    <div v-else class="loading-message">
        <LoadingSpan message="Loading dataset details" />
    </div>
</template>

<style lang="scss" scoped>
@import "~bootstrap/scss/_functions.scss";
@import "theme/blue.scss";

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
    margin-right: 0.5rem;
    white-space: nowrap;
}

.dataset-title {
    font-weight: bold;
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

.state-running,
.state-upload,
.state-setting_metadata,
.state-new,
.state-new_populated_state,
.state-inaccessible {
    background-color: $state-running-bg;
    color: $state-warning-text;
}

.state-paused,
.state-deferred {
    background-color: $state-info-bg;
    color: $state-info-text;
}

.state-queued,
.state-placeholder {
    background-color: $state-default-bg;
    color: $text-color;
}

.state-ok,
.state-empty {
    background-color: $state-success-bg;
    color: $state-success-text;
}

.state-error,
.state-failed_metadata,
.state-discarded,
.state-failed_populated_state {
    background-color: $state-danger-bg;
    color: $state-danger-text;
}

.header-details {
    margin-top: 0.5rem;
    padding-left: 1rem;
    max-height: 500px;
    opacity: 1;
    transition: all 0.25s ease;
    overflow: hidden;
}

.header-enter, /* change to header-enter-from with Vue 3 */
.header-leave-to {
    max-height: 0;
    margin-top: 0;
    padding-top: 0;
    padding-bottom: 0;
    opacity: 0;
}

.dataset-tabs-container {
    min-height: 0;
}

.dataset-tabs-container :deep(.nav-tabs) {
    flex-shrink: 0;
}

.dataset-tabs-container :deep(.tab-content) {
    flex-grow: 1;
    min-height: 0;
    overflow: auto;
}

.dataset-tabs-container :deep(.tab-pane) {
    height: 100%;
    width: 100%;
    display: flex;
    flex-direction: column;
    overflow: auto;
}

.dataset-tabs-container :deep(.iframe-card) {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    padding: 0;
    overflow: hidden;
}

.preview-container {
    position: relative;
    flex-grow: 1;
}

.dataset-preview-iframe {
    border: none;
    width: 100%;
    height: 100%;
}

.iframe-loading {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background-color: $brand-light;
    z-index: 1;
}

.loading-message {
    padding: 2rem;
    text-align: center;
    font-style: italic;
}
</style>
