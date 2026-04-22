<script setup lang="ts">
import { faDownload, faInfoCircle, faRedo, faTable } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRoute } from "vue-router/composables";

import type { HDCASummary } from "@/api";
import { getAppRoot } from "@/onload/loadConfig";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

const route = useRoute();

const props = defineProps<{
    dsc: HDCASummary; // typescript recognizes HDCADetailed IS_A HDCASummary
}>();

const downloadUrl = computed(() => `${getAppRoot()}api/dataset_collections/${props.dsc.id}/download`);
const rerunUrl = computed(() =>
    props.dsc.job_source_type == "Job" ? `/root?job_id=${props.dsc.job_source_id}` : null,
);
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
                <GButton
                    v-if="rerunUrl"
                    title="Rerun job"
                    size="small"
                    color="blue"
                    transparent
                    :pressed="route.fullPath === rerunUrl"
                    :to="rerunUrl">
                    <FontAwesomeIcon fixed-width :icon="faRedo" />
                    <span>Run Job Again</span>
                </GButton>
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
