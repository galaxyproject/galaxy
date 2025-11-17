<script setup lang="ts">
import { faCloudUploadAlt, faLaptop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import { bytesToString } from "@/utils/utils";

import type { UploadMethodConfig } from "../types";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    method: UploadMethodConfig;
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "upload-start"): void;
    (e: "upload-complete", result: { success: boolean; message?: string }): void;
}>();

const isDragging = ref(false);
const selectedFiles = ref<File[]>([]);
const uploadFile = ref<HTMLInputElement | null>(null);

const hasFiles = computed(() => selectedFiles.value.length > 0);
const totalSize = computed(() => {
    const bytes = selectedFiles.value.reduce((sum, file) => sum + file.size, 0);
    return bytesToString(bytes);
});

function onDrop(evt: DragEvent) {
    isDragging.value = false;
    if (evt.dataTransfer?.files) {
        addFiles(evt.dataTransfer.files);
    }
}

function addFiles(fileList: FileList) {
    const newFiles = Array.from(fileList);

    // Filter out duplicates by checking file name and size
    const uniqueNewFiles = newFiles.filter((newFile) => {
        return !selectedFiles.value.some(
            (existingFile) => existingFile.name === newFile.name && existingFile.size === newFile.size,
        );
    });

    selectedFiles.value = [...selectedFiles.value, ...uniqueNewFiles];
}

function addFileFromInput(eventTarget: EventTarget | null) {
    if (!eventTarget) {
        return;
    }
    const { files } = eventTarget as HTMLInputElement;
    if (files) {
        addFiles(files);
    }
}

function removeFile(index: number) {
    selectedFiles.value = selectedFiles.value.filter((_, i) => i !== index);
}

function clearAll() {
    selectedFiles.value = [];
}

function handleBrowse() {
    uploadFile.value?.click();
}

function handleCancel() {
    emit("upload-complete", { success: false, message: "Upload cancelled by user" });
}

function handleStartUpload() {
    console.log("Starting upload of files:", selectedFiles.value);
    console.log("Total files:", selectedFiles.value.length);
    console.log("Total size:", totalSize.value);

    emit("upload-start");

    // Mock upload - in real implementation, this would send files to Galaxy
    setTimeout(() => {
        console.log("Upload completed (mock)");
        emit("upload-complete", {
            success: true,
            message: `Successfully uploaded ${selectedFiles.value.length} file(s)`,
        });
    }, 1000);
}
</script>

<template>
    <div class="local-file-upload">
        <!-- Help Text -->
        <div class="upload-help mb-3">
            <small class="text-muted">
                <strong>Tip:</strong> You can select multiple files at once. Supported formats will be auto-detected.
            </small>
        </div>

        <!-- Drop Zone -->
        <div
            role="button"
            tabindex="0"
            class="drop-zone"
            :class="{ 'drop-zone-active': isDragging, 'has-files': hasFiles }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="onDrop"
            @keydown.enter="handleBrowse"
            @keydown.space.prevent="handleBrowse">
            <div v-if="!hasFiles" class="drop-zone-content">
                <FontAwesomeIcon :icon="faCloudUploadAlt" class="drop-zone-icon" />
                <p class="drop-zone-text">Drag files here</p>
                <p class="drop-zone-subtext">or</p>
                <GButton color="blue" @click="handleBrowse">
                    <FontAwesomeIcon :icon="faLaptop" class="mr-1" />
                    Browse Files
                </GButton>
            </div>

            <!-- File List -->
            <div v-else class="file-list">
                <div class="file-list-header">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="font-weight-bold">{{ selectedFiles.length }} file(s) selected</span>
                        <span class="text-muted">Total: {{ totalSize }}</span>
                    </div>
                </div>
                <div class="file-items-container">
                    <div class="file-items">
                        <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
                            <div class="file-item-info">
                                <span class="file-name" :title="file.name">{{ file.name }}</span>
                                <span class="file-size text-muted">{{ bytesToString(file.size) }}</span>
                            </div>
                            <button class="btn btn-sm btn-link text-danger p-0" @click="removeFile(index)">
                                Remove
                            </button>
                        </div>
                    </div>
                </div>
                <div class="file-list-actions">
                    <GButton color="blue" @click="handleBrowse">
                        <FontAwesomeIcon :icon="faLaptop" class="mr-1" />
                        Add More Files
                    </GButton>
                    <GButton outline color="grey" @click="clearAll"> Clear All </GButton>
                </div>
            </div>

            <!-- Hidden file input -->
            <label for="local-file-input" class="sr-only">Select files to upload</label>
            <input
                id="local-file-input"
                ref="uploadFile"
                type="file"
                multiple
                class="d-none"
                @change="addFileFromInput($event.target)" />
        </div>

        <!-- Upload Actions -->
        <div v-if="hasFiles" class="upload-actions mt-3">
            <GButton outline color="grey" :disabled="!hasFiles" title="Cancel and close" @click="handleCancel">
                <span v-localize>Cancel</span>
            </GButton>
            <GButton
                color="blue"
                :disabled="!hasFiles"
                title="Start uploading files to Galaxy"
                @click="handleStartUpload">
                <span v-localize>Start Upload</span>
            </GButton>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.local-file-upload {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.upload-instructions {
    h5 {
        font-weight: 600;
        color: $text-color;
    }

    p {
        margin-bottom: 0;
        font-size: 0.9rem;
    }
}

.drop-zone {
    border: 2px dashed $border-color;
    border-radius: $border-radius-large;
    padding: 2rem;
    text-align: center;
    transition: all 0.3s ease;
    background-color: $gray-100;
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    min-height: 0;

    &.drop-zone-active {
        border-color: $brand-primary;
        background-color: lighten($brand-primary, 60%);

        .drop-zone-icon {
            color: $brand-primary;
            transform: scale(1.1);
        }

        .drop-zone-text {
            color: $brand-primary;
        }
    }

    &.has-files {
        padding: 1.5rem;
        align-items: stretch;
    }
}

.drop-zone-content {
    width: 100%;
}

.drop-zone-icon {
    font-size: 4rem;
    color: $border-color;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
}

.drop-zone-text {
    font-size: 1.2rem;
    font-weight: 500;
    color: $text-color;
    margin-bottom: 0.5rem;
}

.drop-zone-subtext {
    font-size: 0.9rem;
    color: $text-muted;
    margin-bottom: 1rem;
}

.file-list {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    text-align: left;
    overflow: hidden;
    min-height: 0;
}

.file-list-header {
    flex-shrink: 0;
    border-bottom: 1px solid $border-color;
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
}

.file-items-container {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
}

.file-items {
    padding-right: 0.5rem;
    padding-bottom: 1rem;
}

.file-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    border-radius: $border-radius-base;
    margin-bottom: 0.5rem;
    background-color: $white;
    border: 1px solid $border-color;
    transition: all 0.2s ease;

    &:hover {
        background-color: $gray-100;
        border-color: $brand-primary;
    }
}

.file-item-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.file-name {
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: $text-color;
}

.file-size {
    font-size: 0.85rem;
}

.file-list-actions {
    flex-shrink: 0;
    display: flex;
    gap: 0.5rem;
    justify-content: flex-start;
    padding-top: 1rem;
    border-top: 1px solid $border-color;
}

.upload-actions {
    flex-shrink: 0;
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
}

.upload-help {
    flex-shrink: 0;
    padding: 0.75rem;
    background-color: $gray-100;
    border-radius: $border-radius-base;
    border-left: 3px solid $brand-primary;
}
</style>
