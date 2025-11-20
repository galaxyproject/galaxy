<script setup lang="ts">
import { faCheck, faSpinner, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { bytesToString } from "@/utils/utils";

import type { UploadItem } from "./uploadState";

interface Props {
    uploads: UploadItem[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "show-details"): void;
}>();

const totalProgress = computed(() => {
    if (props.uploads.length === 0) {
        return 0;
    }
    const sum = props.uploads.reduce((acc, file) => acc + file.progress, 0);
    return Math.round(sum / props.uploads.length);
});

const uploadingCount = computed(
    () => props.uploads.filter((f) => f.status === "uploading" || f.status === "processing").length,
);
const completedCount = computed(() => props.uploads.filter((f) => f.status === "completed").length);
const errorCount = computed(() => props.uploads.filter((f) => f.status === "error").length);

const totalSize = computed(() => {
    const bytes = props.uploads.reduce((sum, file) => sum + file.size, 0);
    return bytesToString(bytes);
});

const uploadedSize = computed(() => {
    const bytes = props.uploads.reduce((sum, file) => sum + (file.size * file.progress) / 100, 0);
    return bytesToString(bytes);
});

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
    if (uploadingCount.value > 0 || props.uploads.some((f) => f.status === "queued")) {
        return "Uploading";
    }
    if (props.uploads.length > 0 && completedCount.value === props.uploads.length) {
        return "Upload Complete";
    }
    if (errorCount.value > 0) {
        return "Upload Issues";
    }
    return props.uploads.length === 0 ? "No Uploads" : "Idle";
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
                        <span class="font-weight-bold">{{ statusText }}</span>
                        <span class="text-muted small ml-2">
                            {{ completedCount }}/{{ uploads.length }} files
                            <template v-if="uploadingCount > 0"> • {{ uploadedSize }} / {{ totalSize }} </template>
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
}

.progress-bar-container {
    .progress {
        background-color: $gray-300;
    }

    .progress-bar {
        transition: width 0.3s ease;
    }
}

/* Upload details modal styles now live in parent panel component */
</style>
