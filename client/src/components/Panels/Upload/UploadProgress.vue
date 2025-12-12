<script setup lang="ts">
import {
    faCheck,
    faChevronDown,
    faChevronRight,
    faExclamationTriangle,
    faLayerGroup,
    faSpinner,
    faTimes,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCollapse } from "bootstrap-vue";

import { useUploadQueue } from "@/composables/uploadQueue";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { bytesToString } from "@/utils/utils";

import type { BatchStatus, CollectionBatchState, UploadItem } from "./uploadState";
import { useUploadState } from "./uploadState";

import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";

const uploadQueue = useUploadQueue();
const { batchesWithProgress, standaloneUploads, activeItems, completedCount, errorCount, hasCompleted } =
    useUploadState();

const breadcrumbItems = [{ title: "Import Data", to: "/upload" }, { title: "Upload Progress" }];

// Track expanded batches
const expandedBatches = useUserLocalStorage<string[]>("uploadPanel.expandedBatches", []);

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

function getFileIcon(file: UploadItem) {
    if (file.status === "completed") {
        return faCheck;
    }
    if (file.status === "error") {
        return faTimes;
    }
    return faSpinner;
}

function getFileIconSpin(file: UploadItem) {
    return file.status === "uploading" || file.status === "processing";
}

function getFileStatusClass(file: UploadItem) {
    if (file.status === "completed") {
        return "text-success";
    }
    if (file.status === "error") {
        return "text-danger";
    }
    return "text-primary";
}

function getBatchIcon(batch: CollectionBatchState) {
    if (batch.status === "completed") {
        return faCheck;
    }
    if (batch.status === "error") {
        return faExclamationTriangle;
    }
    if (getBatchIconSpin(batch)) {
        return faSpinner;
    }
    return faLayerGroup;
}

function getBatchIconSpin(batch: CollectionBatchState) {
    return batch.status === "uploading" || batch.status === "creating-collection";
}

function getBatchStatusClass(status: BatchStatus) {
    switch (status) {
        case "completed":
            return "text-success";
        case "error":
            return "text-danger";
        case "creating-collection":
            return "text-info";
        default:
            return "text-primary";
    }
}

function getBatchStatusText(batch: CollectionBatchState & { progress: number }) {
    if (batch.status === "creating-collection") {
        return "Creating collection...";
    }
    if (batch.status === "completed") {
        return "Collection created";
    }
    if (batch.status === "error") {
        return "Error";
    }
    return `${batch.progress}% uploaded`;
}

async function retryBatch(batchId: string) {
    await uploadQueue.retryCollectionCreation(batchId);
}
</script>

<template>
    <div class="upload-progress-view d-flex flex-column h-100">
        <BreadcrumbHeading :items="breadcrumbItems">
            <div v-if="activeItems.length > 0" class="d-flex flex-gapx-1">
                <GButton v-if="hasCompleted" size="small" outline color="grey" @click="uploadQueue.clearCompleted()">
                    Clear Completed
                </GButton>
                <GButton size="small" outline color="grey" @click="uploadQueue.clearAll()"> Clear All </GButton>
            </div>
        </BreadcrumbHeading>

        <div class="upload-progress-content flex-grow-1 overflow-auto p-3">
            <div v-if="activeItems.length > 0 || batchesWithProgress.length > 0" class="h-100 d-flex flex-column">
                <div class="progress-summary mb-3 pb-3 border-bottom">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>{{ completedCount }}/{{ activeItems.length }}</strong>
                            <span class="text-muted ml-1">files completed</span>
                        </div>
                        <div v-if="errorCount > 0" class="text-muted small">{{ errorCount }} error(s)</div>
                    </div>
                </div>

                <div class="file-details-list flex-grow-1 overflow-auto">
                    <!-- Batch groups (collections) -->
                    <div
                        v-for="batch in batchesWithProgress"
                        :key="batch.id"
                        class="batch-group mb-3"
                        :class="{ 'has-error': batch.status === 'error' }">
                        <!-- Batch header -->
                        <div
                            class="batch-header"
                            :class="getBatchStatusClass(batch.status)"
                            role="button"
                            tabindex="0"
                            @click="toggleBatch(batch.id)"
                            @keydown.enter="toggleBatch(batch.id)"
                            @keydown.space.prevent="toggleBatch(batch.id)">
                            <FontAwesomeIcon
                                :icon="getBatchIcon(batch)"
                                :spin="getBatchIconSpin(batch)"
                                class="mr-2"
                                fixed-width />
                            <span class="batch-name">{{ batch.name }}</span>
                            <span class="batch-type badge badge-secondary ml-2">{{ batch.type }}</span>
                            <span class="batch-status ml-auto mr-2">{{ getBatchStatusText(batch) }}</span>
                            <FontAwesomeIcon
                                :icon="isExpanded(batch.id) ? faChevronDown : faChevronRight"
                                class="expand-icon"
                                fixed-width />
                        </div>

                        <!-- Batch error message with retry button -->
                        <div v-if="batch.error" class="batch-error mt-2 p-2">
                            <span class="text-danger">{{ batch.error }}</span>
                            <GButton size="small" class="ml-2" @click="retryBatch(batch.id)"> Retry </GButton>
                        </div>

                        <!-- Batch progress bar -->
                        <div
                            v-if="batch.status !== 'completed'"
                            class="progress batch-progress mt-2"
                            style="height: 4px">
                            <div
                                class="progress-bar"
                                :class="{
                                    'bg-info': batch.status === 'creating-collection',
                                    'bg-danger': batch.status === 'error',
                                }"
                                :style="{ width: `${batch.progress}%` }"
                                role="progressbar"
                                :aria-valuenow="batch.progress"
                                aria-valuemin="0"
                                aria-valuemax="100"></div>
                        </div>

                        <!-- Collapsible upload items -->
                        <BCollapse :visible="isExpanded(batch.id)" class="batch-uploads mt-2">
                            <div
                                v-for="(file, index) in batch.uploads"
                                :key="index"
                                class="file-detail-item nested"
                                :class="{ 'has-error': file.status === 'error' }">
                                <div class="d-flex align-items-center mb-1">
                                    <FontAwesomeIcon
                                        :icon="getFileIcon(file)"
                                        :class="getFileStatusClass(file)"
                                        :spin="getFileIconSpin(file)"
                                        class="mr-2"
                                        fixed-width
                                        size="sm" />
                                    <span class="file-name flex-grow-1" :title="file.name">{{ file.name }}</span>
                                    <span class="text-muted small ml-2">{{ bytesToString(file.size) }}</span>
                                    <span class="text-muted small ml-2">{{ file.progress }}%</span>
                                </div>
                                <div class="progress" style="height: 3px">
                                    <div
                                        class="progress-bar"
                                        :class="{
                                            'bg-success': file.status === 'completed',
                                            'bg-danger': file.status === 'error',
                                        }"
                                        :style="{ width: `${file.progress}%` }"
                                        role="progressbar"
                                        :aria-valuenow="file.progress"
                                        aria-valuemin="0"
                                        aria-valuemax="100"></div>
                                </div>
                                <div v-if="file.error" class="error-message text-danger small mt-1">
                                    {{ file.error }}
                                </div>
                            </div>
                        </BCollapse>
                    </div>

                    <!-- Standalone uploads (not part of any collection) -->
                    <div
                        v-for="(file, index) in standaloneUploads"
                        :key="index"
                        class="file-detail-item"
                        :class="{ 'has-error': file.status === 'error' }">
                        <div class="d-flex align-items-center mb-1">
                            <FontAwesomeIcon
                                :icon="getFileIcon(file)"
                                :class="getFileStatusClass(file)"
                                :spin="file.status === 'uploading' || file.status === 'processing'"
                                class="mr-2"
                                fixed-width
                                size="sm" />
                            <span class="file-name flex-grow-1" :title="file.name">{{ file.name }}</span>
                            <span class="text-muted small ml-2">{{ bytesToString(file.size) }}</span>
                            <span class="text-muted small ml-2">{{ file.progress }}%</span>
                        </div>
                        <div class="progress" style="height: 3px">
                            <div
                                class="progress-bar"
                                :class="{
                                    'bg-success': file.status === 'completed',
                                    'bg-danger': file.status === 'error',
                                }"
                                :style="{ width: `${file.progress}%` }"
                                role="progressbar"
                                :aria-valuenow="file.progress"
                                aria-valuemin="0"
                                aria-valuemax="100"></div>
                        </div>
                        <div v-if="file.error" class="error-message text-danger small mt-1">
                            {{ file.error }}
                        </div>
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

.upload-progress-view {
    background-color: $white;
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

.batch-group {
    margin-bottom: 1rem;
    border: 1px solid $border-color;
    border-radius: $border-radius-base;
    background-color: $white;

    &.has-error {
        border-color: lighten($brand-danger, 30%);
        background-color: lighten($brand-danger, 48%);
    }
}

.batch-header {
    display: flex;
    align-items: center;
    padding: 0.75rem;
    cursor: pointer;
    font-weight: 600;
    font-size: 0.95rem;
    background-color: $gray-100;
    border-radius: $border-radius-base $border-radius-base 0 0;
    transition: background-color 0.15s ease;

    &:hover {
        background-color: $gray-200;
    }

    &:focus {
        outline: 2px solid $brand-primary;
        outline-offset: -2px;
    }
}

.batch-name {
    flex-shrink: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.batch-type {
    flex-shrink: 0;
    font-size: 0.75rem;
    font-weight: 500;
}

.batch-status {
    flex-shrink: 0;
    font-size: 0.85rem;
    font-weight: normal;
}

.expand-icon {
    flex-shrink: 0;
    transition: transform 0.2s ease;
}

.batch-progress {
    margin: 0 0.75rem 0.5rem 0.75rem;
}

.batch-error {
    margin: 0 0.75rem;
    padding: 0.5rem;
    background-color: lighten($brand-danger, 45%);
    border: 1px solid lighten($brand-danger, 30%);
    border-radius: $border-radius-base;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.batch-uploads {
    padding: 0.5rem 0.75rem 0.75rem 0.75rem;
}

.file-detail-item {
    padding: 0.75rem;
    border-radius: $border-radius-base;
    margin-bottom: 0.5rem;
    background-color: $gray-100;
    border: 1px solid $border-color;

    &.nested {
        background-color: $white;
        margin-left: 0;
    }

    &:last-child {
        margin-bottom: 0;
    }

    &.has-error {
        background-color: lighten($brand-danger, 45%);
        border-color: lighten($brand-danger, 30%);
    }
}

.file-name {
    font-size: 0.9rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.error-message {
    padding-left: 1.5rem;
}
</style>
