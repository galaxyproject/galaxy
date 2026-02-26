<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";

import { useUploadQueue } from "@/composables/uploadQueue";
import { useUserLocalStorage } from "@/composables/userLocalStorage";

import { getUploadRootBreadcrumb } from "./uploadBreadcrumb";
import { useUploadState } from "./uploadState";

import BatchUploadGroup from "./BatchUploadGroup.vue";
import UploadFileRow from "./UploadFileRow.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";

const uploadQueue = useUploadQueue();
const uploadState = useUploadState();
const { orderedUploadItems, batchesWithProgress, standaloneUploads, activeItems, hasCompleted } = uploadState;

const breadcrumbItems = [getUploadRootBreadcrumb("/upload"), { title: "Upload Progress" }];

const fileListRef = ref<HTMLElement | null>(null);
const expandedBatches = useUserLocalStorage<string[]>("uploadPanel.expandedBatches", []);

function cleanupExpandedBatches() {
    const currentBatchIds = new Set(uploadState.activeBatches.value.map((b) => b.id));
    expandedBatches.value = expandedBatches.value.filter((id) => currentBatchIds.has(id));
}

// Clean up stale batch IDs from expandedBatches (one-time on mount)
cleanupExpandedBatches();

function isExpanded(batchId: string): boolean {
    return expandedBatches.value.includes(batchId);
}

function toggleBatch(batchId: string) {
    const index = expandedBatches.value.indexOf(batchId);
    if (index > -1) {
        expandedBatches.value.splice(index, 1);
    } else {
        expandedBatches.value.push(batchId);
    }
}

function onClearCompleted() {
    uploadQueue.clearCompleted();
    cleanupExpandedBatches();
}

function onClearAll() {
    uploadQueue.clearAll();
    cleanupExpandedBatches();
}

async function retryBatch(batchId: string) {
    await uploadQueue.retryCollectionCreation(batchId);
}

const uploadItemCount = computed(() => {
    return batchesWithProgress.value.length + standaloneUploads.value.length;
});

watch(uploadItemCount, async (newCount, oldCount) => {
    if (newCount > oldCount) {
        await nextTick();
        fileListRef.value?.scrollTo({
            top: fileListRef.value.scrollHeight,
            behavior: "smooth",
        });
    }
});

onMounted(() => {
    nextTick(() => {
        fileListRef.value?.scrollTo({
            top: fileListRef.value.scrollHeight,
            behavior: "auto",
        });
    });
});
</script>

<template>
    <div class="upload-progress-view d-flex flex-column h-100">
        <BreadcrumbHeading :items="breadcrumbItems">
            <div v-if="activeItems.length > 0" class="d-flex flex-gapx-1">
                <GButton v-if="hasCompleted" size="small" outline color="grey" @click="onClearCompleted()">
                    Clear Completed
                </GButton>
                <GButton size="small" outline color="grey" @click="onClearAll()"> Clear All </GButton>
            </div>
        </BreadcrumbHeading>

        <div class="upload-progress-content flex-grow-1 overflow-auto p-3">
            <div v-if="activeItems.length > 0 || batchesWithProgress.length > 0" class="h-100 d-flex flex-column">
                <div ref="fileListRef" class="file-details-list flex-grow-1 overflow-auto">
                    <div
                        v-for="item in orderedUploadItems"
                        :key="item.type === 'batch' ? item.batch.id : item.upload.id">
                        <BatchUploadGroup
                            v-if="item.type === 'batch'"
                            :batch="item.batch"
                            :expanded="isExpanded(item.batch.id)"
                            @toggle="toggleBatch(item.batch.id)"
                            @retry="retryBatch(item.batch.id)" />

                        <UploadFileRow v-else :file="item.upload" />
                    </div>
                </div>
            </div>
            <div v-else class="d-flex flex-column align-items-center justify-content-center h-100 text-muted">
                <p class="h-lg mb-3">No uploads in progress</p>
                <p class="text-muted">
                    Start a new upload from the <router-link to="/upload">Import Data</router-link> page.
                </p>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.upload-progress-content {
    min-width: 480px;
}

.progress-summary {
    flex-shrink: 0;
}

.file-details-list {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 0.5rem;
    min-height: 0;
}
</style>
