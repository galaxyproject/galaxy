<script setup lang="ts">
import { faDownload, faInfoCircle, faRedo, faTable } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import type { HDCASummary } from "@/api";
import { getAppRoot } from "@/onload/loadConfig";

const router = useRouter();

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

const sheetUrl = computed(() => {
    return `${getAppRoot()}collection/${props.dsc.id}/sheet`;
});

function onDownload() {
    window.location.href = downloadUrl.value;
}
</script>
<template>
    <section>
        <nav class="content-operations d-flex justify-content-between bg-secondary">
            <b-button-group>
                <b-button
                    title="Download Collection"
                    :disabled="disableDownload"
                    class="rounded-0 text-decoration-none"
                    size="sm"
                    variant="link"
                    :href="downloadUrl"
                    @click="onDownload">
                    <FontAwesomeIcon class="mr-1" :icon="faDownload" />
                    <span>Download</span>
                </b-button>
                <b-button
                    v-if="showCollectionDetailsUrl"
                    class="collection-job-details-btn px-1"
                    title="Show Details"
                    size="sm"
                    variant="link"
                    :href="showCollectionDetailsUrl"
                    @click.prevent.stop="router.push(showCollectionDetailsUrl)">
                    <FontAwesomeIcon class="mr-1" :icon="faInfoCircle" />
                    <span>Show Details</span>
                </b-button>
                <b-button
                    v-if="rerunUrl"
                    title="Rerun job"
                    class="rounded-0 text-decoration-none"
                    size="sm"
                    variant="link"
                    :href="rerunUrl"
                    @click.prevent.stop="router.push(rerunUrl)">
                    <FontAwesomeIcon class="mr-1" :icon="faRedo" />
                    <span>Run Job Again</span>
                </b-button>
                <b-button
                    v-if="sheetUrl"
                    class="rounded-0 text-decoration-none"
                    size="sm"
                    variant="link"
                    :href="sheetUrl"
                    @click.prevent.stop="router.push(sheetUrl)">
                    <FontAwesomeIcon class="mr-1" :icon="faTable" />
                    <span>View Sheet</span>
                </b-button>
            </b-button-group>
        </nav>
    </section>
</template>
