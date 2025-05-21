<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBug, faChartBar, faEye, faInfoCircle, faPen } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BNav, BNavItem } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { usePersistentToggle } from "@/composables/persistentToggle";
import { useDatasetStore } from "@/stores/datasetStore";
import { useDatatypeVisualizationsStore } from "@/stores/datatypeVisualizationsStore";

import DatasetError from "../DatasetInformation/DatasetError.vue";
import LoadingSpan from "../LoadingSpan.vue";
import DatasetState from "./DatasetState.vue";
import Heading from "@/components/Common/Heading.vue";
import DatasetAttributes from "@/components/DatasetInformation/DatasetAttributes.vue";
import DatasetDetails from "@/components/DatasetInformation/DatasetDetails.vue";
import VisualizationsList from "@/components/Visualizations/Index.vue";
import VisualizationFrame from "@/components/Visualizations/VisualizationFrame.vue";
import CenterFrame from "@/entry/analysis/modules/CenterFrame.vue";

library.add(faEye, faChartBar, faInfoCircle, faPen, faBug);

const datasetStore = useDatasetStore();
const datatypeVisualizationsStore = useDatatypeVisualizationsStore();
const { toggled: headerCollapsed, toggle: toggleHeaderCollapse } = usePersistentToggle("dataset-header-collapsed");

interface Props {
    datasetId: string;
    tab?: "details" | "edit" | "error" | "preview" | "visualize";
}

const props = withDefaults(defineProps<Props>(), {
    tab: "preview",
});

const iframeLoading = ref(true);
const preferredVisualization = ref<string>();

const dataset = computed(() => datasetStore.getDataset(props.datasetId));
const headerState = computed(() => (headerCollapsed.value ? "closed" : "open"));
const isLoading = computed(() => datasetStore.isLoadingDataset(props.datasetId));
const showError = computed(
    () => dataset.value && (dataset.value.state === "error" || dataset.value.state === "failed_metadata")
);

// Check if the dataset has a preferred visualization by datatype
async function checkPreferredVisualization() {
    if (dataset.value && dataset.value.file_ext) {
        try {
            const mapping = await datatypeVisualizationsStore.getPreferredVisualizationForDatatype(
                dataset.value.file_ext
            );
            if (mapping) {
                preferredVisualization.value = mapping.visualization;
            } else {
                preferredVisualization.value = undefined;
            }
        } catch (error) {
            preferredVisualization.value = undefined;
        }
    } else {
        preferredVisualization.value = undefined;
    }
}

// Watch for changes to the dataset to check for preferred visualizations
watch(() => dataset.value?.file_ext, checkPreferredVisualization, { immediate: true });
</script>

<template>
    <LoadingSpan v-if="isLoading || !dataset" message="Loading dataset details" />
    <div v-else class="dataset-view d-flex flex-column h-100">
        <header :key="`dataset-header-${dataset.id}`" class="dataset-header flex-shrink-0">
            <div class="d-flex">
                <Heading
                    h1
                    separator
                    inline
                    size="lg"
                    class="flex-grow-1"
                    :collapse="headerState"
                    @click="toggleHeaderCollapse">
                    {{ dataset?.hid }}: <span class="font-weight-bold">{{ dataset?.name }}</span>
                    <span class="dataset-state-header">
                        <DatasetState :dataset-id="datasetId" />
                    </span>
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
                    <div v-if="dataset.misc_info" class="info">
                        <span class="value">{{ dataset.misc_info }}</span>
                    </div>
                </div>
            </transition>
        </header>
        <BNav pills class="my-2 p-2 bg-light border-bottom">
            <BNavItem title="Preview" :active="tab === 'preview'" :to="`/datasets/${datasetId}/preview`">
                <FontAwesomeIcon :icon="faEye" class="mr-1" /> Preview
            </BNavItem>
            <BNavItem
                v-if="!showError"
                title="Visualize"
                :active="tab === 'visualize'"
                :to="`/datasets/${datasetId}/visualize`">
                <FontAwesomeIcon :icon="faChartBar" class="mr-1" /> Visualize
            </BNavItem>
            <BNavItem title="Details" :active="tab === 'details'" :to="`/datasets/${datasetId}/details`">
                <FontAwesomeIcon :icon="faInfoCircle" class="mr-1" /> Details
            </BNavItem>
            <BNavItem title="Edit" :active="tab === 'edit'" :to="`/datasets/${datasetId}/edit`">
                <FontAwesomeIcon :icon="faPen" class="mr-1" /> Edit
            </BNavItem>
            <BNavItem v-if="showError" title="Error" :active="tab === 'error'" :to="`/datasets/${datasetId}/error`">
                <FontAwesomeIcon :icon="faBug" class="mr-1" /> Error
            </BNavItem>
        </BNav>
        <div v-if="tab === 'preview'" class="h-100">
            <VisualizationFrame
                v-if="preferredVisualization"
                :dataset-id="datasetId"
                :visualization="preferredVisualization"
                @load="iframeLoading = false" />
            <CenterFrame
                v-else
                :src="`/datasets/${datasetId}/display/?preview=True`"
                :is_preview="true"
                @load="iframeLoading = false" />
        </div>
        <div v-else-if="tab === 'visualize'" class="d-flex flex-column overflow-hidden overflow-y">
            <VisualizationsList :dataset-id="datasetId" />
        </div>
        <div v-else-if="tab === 'edit'" class="d-flex flex-column overflow-hidden overflow-y mt-2">
            <DatasetAttributes :dataset-id="datasetId" />
        </div>
        <div v-else-if="tab === 'details'" class="d-flex flex-column overflow-hidden overflow-y mt-2">
            <DatasetDetails :dataset-id="datasetId" />
        </div>
        <div v-else-if="tab === 'error'" class="d-flex flex-column overflow-hidden overflow-y mt-2">
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
}

.header-enter, /* change to header-enter-from with Vue 3 */
.header-leave-to {
    max-height: 0;
    margin-top: 0;
    padding-top: 0;
    padding-bottom: 0;
    opacity: 0;
}

.dataset-state-header {
    font-size: $h5-font-size;
    vertical-align: middle;
}
</style>
