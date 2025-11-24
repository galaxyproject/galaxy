<script setup lang="ts">
import { faCheck, faSpinner, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { bytesToString } from "@/utils/utils";

import { useUploadService } from "./uploadService";
import type { UploadItem } from "./uploadState";
import { useUploadState } from "./uploadState";

import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";

const uploadService = useUploadService();
const { activeItems, completedCount, errorCount, isUploading, hasCompleted } = useUploadState();

const breadcrumbItems = [{ title: "Import Data", to: "/upload" }, { title: "Upload Progress" }];

function getFileIcon(file: UploadItem) {
    if (file.status === "completed") {
        return faCheck;
    }
    if (file.status === "error") {
        return faTimes;
    }
    return faSpinner;
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
</script>

<template>
    <div class="upload-progress-view d-flex flex-column h-100">
        <BreadcrumbHeading :items="breadcrumbItems" />

        <div class="upload-progress-content flex-grow-1 overflow-auto p-3">
            <div v-if="activeItems.length > 0" class="h-100 d-flex flex-column">
                <div class="progress-summary mb-3 pb-3 border-bottom">
                    <h2 class="h-lg mb-2">Upload Status</h2>
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>{{ completedCount }}/{{ activeItems.length }}</strong>
                            <span class="text-muted ml-1">files completed</span>
                        </div>
                        <div v-if="isUploading" class="text-muted small">
                            <span v-if="errorCount > 0">{{ errorCount }} error(s)</span>
                        </div>
                    </div>
                </div>

                <div class="clear-actions mb-3">
                    <GButton v-if="hasCompleted" outline color="grey" @click="uploadService.clearCompleted()">
                        Clear Completed
                    </GButton>
                    <GButton outline color="grey" @click="uploadService.clearAll()"> Clear All </GButton>
                </div>

                <div class="file-details-list flex-grow-1 overflow-auto">
                    <div
                        v-for="(file, index) in activeItems"
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

.clear-actions {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
    flex-shrink: 0;
}

.file-details-list {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 0.5rem;
    min-height: 0;
}

.file-detail-item {
    padding: 0.75rem;
    border-radius: $border-radius-base;
    margin-bottom: 0.5rem;
    background-color: $gray-100;
    border: 1px solid $border-color;

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
