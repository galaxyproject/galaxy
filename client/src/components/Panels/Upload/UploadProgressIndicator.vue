<script setup lang="ts">
import { faCheck, faSpinner, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { useUploadState } from "./uploadState";

const { activeItems: uploads, completedCount, errorCount, uploadingCount, totalProgress } = useUploadState();

const emit = defineEmits<{
    (e: "show-details"): void;
}>();

const statusIcon = computed(() => {
    if (errorCount.value > 0) {
        return faTimes;
    }
    if (uploadingCount.value > 0) {
        return faSpinner;
    }
    return faCheck;
});

const statusClass = computed(() => {
    if (errorCount.value > 0) {
        return "text-danger";
    }
    if (uploadingCount.value > 0) {
        return "text-primary";
    }
    return "text-success";
});

const statusText = computed(() => {
    if (uploadingCount.value > 0 || uploads.value.some((f) => f.status === "queued")) {
        return "Uploading";
    }
    if (uploads.value.length > 0 && completedCount.value === uploads.value.length) {
        return "Upload Complete";
    }
    if (errorCount.value > 0) {
        return "Upload Issues";
    }
    return uploads.value.length === 0 ? "No Uploads" : "Idle";
});

function showDetails() {
    emit("show-details");
}
</script>

<template>
    <div v-if="uploads.length > 0" class="upload-progress-indicator">
        <div
            role="button"
            tabindex="0"
            class="progress-card"
            @click="showDetails"
            @keydown.enter="showDetails"
            @keydown.space.prevent="showDetails">
            <div class="progress-header">
                <div class="d-flex align-items-center flex-grow-1">
                    <FontAwesomeIcon :icon="statusIcon" :class="statusClass" :spin="uploadingCount > 0" class="mr-2" />
                    <div class="progress-summary">
                        <span class="font-weight-bold status-text">{{ statusText }}</span>
                        <span class="text-muted small ml-2 file-info">
                            {{ completedCount }}/{{ uploads.length }} files
                        </span>
                    </div>
                </div>
            </div>
            <div class="progress-bar-container mt-2">
                <div class="progress" style="height: 4px">
                    <div
                        class="progress-bar"
                        :class="{
                            'bg-success': totalProgress === 100 && errorCount === 0,
                            'bg-danger': errorCount > 0,
                        }"
                        :style="{ width: `${totalProgress}%` }"
                        role="progressbar"
                        :aria-valuenow="totalProgress"
                        aria-valuemin="0"
                        aria-valuemax="100"></div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.upload-progress-indicator {
    margin-bottom: 0.75rem;
}

.progress-card {
    background-color: $white;
    border: 1px solid $border-color;
    border-radius: $border-radius-base;
    padding: 0.75rem;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
        background-color: $gray-100;
        border-color: $brand-primary;
    }
}

.progress-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.progress-summary {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    min-width: 0;
}

.status-text {
    white-space: nowrap;
}

.file-info {
    white-space: nowrap;
}

.progress-bar-container {
    .progress {
        background-color: $gray-300;
    }

    .progress-bar {
        transition: width 0.3s ease;
    }
}
</style>
