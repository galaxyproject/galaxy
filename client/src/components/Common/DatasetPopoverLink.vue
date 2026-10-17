<script setup lang="ts">
import { BPopover } from "bootstrap-vue";
import { computed, ref } from "vue";

import { useDatasetStore } from "@/stores/datasetStore";
import localize from "@/utils/localization";

import DatasetInformation from "@/components/DatasetInformation/DatasetInformation.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    datasetId: string;
}>();

const datasetStore = useDatasetStore();

const targetId = computed(() => `storage-run-item-dataset-${props.datasetId}`);

const popoverShown = ref(false);

// The getter fetches when read, and refetches after a retry backoff; use it only while the popover is shown.
const details = computed(() =>
    popoverShown.value ? datasetStore.getDataset(props.datasetId) : datasetStore.storedDatasets[props.datasetId],
);
const loading = computed(() => datasetStore.isLoadingDataset(props.datasetId));
const loadError = computed(() => datasetStore.getDatasetError(props.datasetId)?.message);

async function ensureDatasetDetails() {
    if (details.value || loading.value) {
        return;
    }

    await datasetStore.fetchDataset({ id: props.datasetId });
}
</script>

<template>
    <div>
        <router-link
            :id="targetId"
            class="text-monospace"
            :to="`/datasets/${datasetId}/details`"
            @mouseenter.native="ensureDatasetDetails"
            @focus.native="ensureDatasetDetails">
            {{ datasetId }}
        </router-link>

        <BPopover
            :target="targetId"
            triggers="hover focus"
            boundary="window"
            placement="right"
            @show="popoverShown = true"
            @hidden="popoverShown = false">
            <div class="dataset-details-popover">
                <div v-if="loading">
                    <LoadingSpan :message="localize('Loading dataset details')" />
                </div>
                <div v-else-if="loadError" class="text-danger">
                    {{ loadError }}
                </div>
                <div v-else-if="details">
                    <DatasetInformation :dataset="details" />
                </div>
            </div>
        </BPopover>
    </div>
</template>

<style scoped>
:deep(.dataset-details-popover) {
    max-width: 420px;
}
</style>
