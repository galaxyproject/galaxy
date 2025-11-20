<script setup lang="ts">
import { faCheck, faSpinner, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { bytesToString } from "@/utils/utils";

import { useUploadService } from "./uploadService";
import type { UploadItem } from "./uploadState";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    uploads: UploadItem[];
}

defineProps<Props>();

const uploadService = useUploadService();

const hasCompleted = computed(() => {
    return uploadService.state.activeItems.value.some((u) => u.status === "completed");
});

const hasAny = computed(() => {
    return uploadService.state.activeItems.value.length > 0;
});

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
    <div class="upload-details-modal">
        <div v-if="hasAny" class="clear-actions mb-2">
            <GButton v-if="hasCompleted" outline color="grey" @click="uploadService.clearCompleted()">
                Clear Completed
            </GButton>
            <GButton outline color="grey" @click="uploadService.clearAll()"> Clear All </GButton>
        </div>
        <div class="file-details-list">
            <div
                v-for="(file, index) in uploads"
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
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.upload-details-modal {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
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
    margin-top: 1rem;
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
