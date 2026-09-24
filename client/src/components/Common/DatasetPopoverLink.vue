<script setup lang="ts">
import { BPopover } from "bootstrap-vue";
import { computed } from "vue";

import { useDatasetStore } from "@/stores/datasetStore";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";

import DatasetInformation from "@/components/DatasetInformation/DatasetInformation.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    datasetId: string;
}>();

const datasetStore = useDatasetStore();
const historyStore = useHistoryStore();

const targetId = computed(() => `storage-run-item-dataset-${props.datasetId}`);

const details = computed(() => datasetStore.storedDatasets[props.datasetId]);
const loading = computed(() => datasetStore.isLoadingDataset(props.datasetId));
const loadError = computed(() => datasetStore.getDatasetError(props.datasetId)?.message);

async function ensureDatasetDetails() {
    if (details.value || loading.value) {
        return;
    }

    await datasetStore.fetchDataset({ id: props.datasetId });

    // If dataset has a history_id, ensure the history is loaded
    const datasetDetails = datasetStore.storedDatasets[props.datasetId];
    if (datasetDetails?.history_id && !historyStore.getHistoryById(datasetDetails.history_id)) {
        await historyStore.loadHistoryById(datasetDetails.history_id);
    }
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

        <BPopover :target="targetId" triggers="hover focus" boundary="window" placement="right">
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
