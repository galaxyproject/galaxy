<script setup lang="ts">
import { faCheckSquare } from "@fortawesome/free-regular-svg-icons";
import { faDownload, faInfoCircle, faLayerGroup, faTable } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRoute } from "vue-router/composables";

import type { HDCASummary } from "@/api";
import { getAppRoot } from "@/onload/loadConfig";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";
import RerunJobButton from "@/components/JobInformation/RerunJobButton.vue";

const route = useRoute();

const props = defineProps<{
    dsc: HDCASummary; // typescript recognizes HDCADetailed IS_A HDCASummary
    /** Whether the element selectors are shown, so the toggle can reflect it. */
    showSelection?: boolean;
    /** How many elements are selected, to label the build action. */
    selectionSize?: number;
    /** Selection is only offered where the collection can be worked with. */
    selectable?: boolean;
}>();

const emit = defineEmits<{
    (e: "update:show-selection", show: boolean): void;
    (e: "build-collection"): void;
}>();

const downloadUrl = computed(() => `${getAppRoot()}api/dataset_collections/${props.dsc.id}/download`);
const showCollectionDetailsUrl = computed(() =>
    props.dsc.job_source_type == "Job" ? `/jobs/${props.dsc.job_source_id}/view` : null,
);
const disableDownload = props.dsc.populated_state !== "ok";

const hasSampleSheet = computed(() => {
    return props.dsc.collection_type && props.dsc.collection_type.startsWith("sample_sheet");
});

const sheetUrl = computed(() => `/collection/${props.dsc.id}/sheet`);
</script>
<template>
    <section>
        <nav class="content-operations d-flex justify-content-between bg-secondary">
            <GButtonGroup class="collection-operations-btn-group">
                <GButton
                    v-if="props.selectable"
                    tooltip
                    title="Select Items"
                    class="show-collection-content-selectors-btn rounded-0"
                    size="small"
                    color="blue"
                    transparent
                    :pressed="props.showSelection"
                    @click="emit('update:show-selection', !props.showSelection)">
                    <FontAwesomeIcon :icon="faCheckSquare" fixed-width />
                </GButton>
                <GButton
                    v-if="props.showSelection && props.selectionSize"
                    title="Build a new list from the selected datasets"
                    size="small"
                    color="blue"
                    transparent
                    @click="emit('build-collection')">
                    <FontAwesomeIcon fixed-width :icon="faLayerGroup" />
                    <span>Build List ({{ props.selectionSize }})</span>
                </GButton>
                <GButton
                    title="Download Collection"
                    :disabled="disableDownload"
                    size="small"
                    color="blue"
                    transparent
                    :href="downloadUrl">
                    <FontAwesomeIcon fixed-width :icon="faDownload" />
                    <span>Download</span>
                </GButton>
                <GButton
                    v-if="showCollectionDetailsUrl"
                    class="collection-job-details-btn"
                    title="Show Details"
                    size="small"
                    color="blue"
                    transparent
                    :pressed="route.fullPath === showCollectionDetailsUrl"
                    :to="showCollectionDetailsUrl">
                    <FontAwesomeIcon fixed-width :icon="faInfoCircle" />
                    <span>Show Details</span>
                </GButton>
                <RerunJobButton
                    v-if="props.dsc.job_source_type === 'Job' && props.dsc.job_source_id"
                    :job-id="props.dsc.job_source_id" />
                <GButton
                    v-if="hasSampleSheet && sheetUrl"
                    title="View Sample Sheet"
                    size="small"
                    color="blue"
                    transparent
                    :pressed="route.fullPath === sheetUrl"
                    :to="sheetUrl">
                    <FontAwesomeIcon fixed-width :icon="faTable" />
                    <span>View Sheet</span>
                </GButton>
            </GButtonGroup>
        </nav>
    </section>
</template>

<style scoped lang="scss">
.collection-operations-btn-group {
    display: flex;
    flex-wrap: wrap;
    :deep(.g-button) {
        border-radius: 0;
        white-space: nowrap;
    }
}
</style>
