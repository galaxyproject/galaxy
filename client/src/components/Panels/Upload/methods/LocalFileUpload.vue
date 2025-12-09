<script setup lang="ts">
import { faCloudUploadAlt, faExclamationTriangle, faLaptop, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormCheckbox, BFormInput, BFormSelect, BTable } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { findExtension } from "@/components/Upload/utils";
import { useFileDrop } from "@/composables/fileDrop";
import { useUploadConfigurations } from "@/composables/uploadConfigurations";
import { useUploadQueue } from "@/composables/uploadQueue";
import { bytesToString } from "@/utils/utils";

import type { UploadMethodComponent, UploadMethodConfig } from "../types";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    method: UploadMethodConfig;
    targetHistoryId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "ready", ready: boolean): void;
}>();

const uploadQueue = useUploadQueue();

const {
    configOptions,
    effectiveExtensions,
    listDbKeys,
    ready: configurationsReady,
} = useUploadConfigurations(undefined);

interface FileWithMetadata {
    file: File;
    name: string;
    extension: string;
    dbKey: string;
    spaceToTab: boolean;
    toPosixLines: boolean;
}

const selectedFiles = ref<FileWithMetadata[]>([]);
const uploadFile = ref<HTMLInputElement | null>(null);
const dropZoneElement = ref<HTMLElement | null>(null);

const hasFiles = computed(() => selectedFiles.value.length > 0);
const totalSize = computed(() => {
    const bytes = selectedFiles.value.reduce((sum, item) => sum + item.file.size, 0);
    return bytesToString(bytes);
});

// Bulk selectors
const bulkExtension = ref<string | null>(null);
const bulkDbKey = ref<string | null>(null);

const bulkExtensionWarning = computed(() => {
    if (!bulkExtension.value) {
        return null;
    }
    const ext = findExtension(effectiveExtensions.value, bulkExtension.value);
    return ext?.upload_warning || null;
});

function setAllExtensions(extension: string | null) {
    if (extension) {
        selectedFiles.value.forEach((file) => {
            file.extension = extension;
        });
    }
}

function setAllDbKeys(dbKey: string | null) {
    if (dbKey) {
        selectedFiles.value.forEach((file) => {
            file.dbKey = dbKey;
        });
    }
}

const tableFields = [
    { key: "name", label: "Name", sortable: false, tdClass: "file-name-cell" },
    { key: "extension", label: "Type", sortable: false, thStyle: { minWidth: "180px" } },
    { key: "dbKey", label: "Database", sortable: false, thStyle: { minWidth: "200px" } },
    { key: "size", label: "Size", sortable: false, thStyle: { width: "100px" } },
    { key: "options", label: "Options", sortable: false },
    { key: "actions", label: "", sortable: false, tdClass: "text-right", thStyle: { width: "50px" } },
];

watch(hasFiles, (ready) => emit("ready", ready), { immediate: true });

function onDrop(evt: DragEvent) {
    if (evt.dataTransfer?.files) {
        addFiles(evt.dataTransfer.files);
    }
}

const { isFileOverDropZone } = useFileDrop(dropZoneElement, onDrop, () => {}, false);

function addFiles(files: FileList | File[] | null) {
    if (!files) {
        return;
    }

    const fileArray = Array.from(files);

    const defaultExtension = configOptions.value?.defaultExtension || "auto";
    const defaultDbKey = configOptions.value?.defaultDbKey || "?";

    for (const file of fileArray) {
        selectedFiles.value.push({
            file,
            name: file.name,
            extension: defaultExtension,
            dbKey: defaultDbKey,
            spaceToTab: false,
            toPosixLines: false,
        });
    }
}

function removeFile(index: number) {
    selectedFiles.value.splice(index, 1);
}

function addFileFromInput(eventTarget: EventTarget | null) {
    const files = (eventTarget as HTMLInputElement)?.files;
    if (files) {
        addFiles(files);
    }
}

function handleBrowse() {
    uploadFile.value?.click();
}

function clearAll() {
    selectedFiles.value = [];
}

function startUpload() {
    const uploads = selectedFiles.value.map((item) => ({
        uploadMode: "local-file" as const,
        name: item.name,
        size: item.file.size,
        targetHistoryId: props.targetHistoryId,
        dbkey: item.dbKey,
        extension: item.extension,
        spaceToTab: item.spaceToTab,
        toPosixLines: item.toPosixLines,
        deferred: false,
        fileData: item.file,
    }));

    uploadQueue.enqueue(uploads);
    selectedFiles.value = [];
}

defineExpose<UploadMethodComponent>({ startUpload });
</script>

<template>
    <div class="local-file-upload">
        <!-- Drop Zone -->
        <div
            ref="dropZoneElement"
            role="button"
            tabindex="0"
            class="drop-zone"
            data-galaxy-file-drop-target
            :class="{ 'drop-zone-active': isFileOverDropZone, 'has-files': hasFiles }"
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

            <!-- File Table with Metadata Editing -->
            <div v-else class="file-list">
                <div class="file-list-header">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="font-weight-bold">{{ selectedFiles.length }} file(s) selected</span>
                        <span class="text-muted">Total: {{ totalSize }}</span>
                    </div>
                </div>

                <div class="file-table-container">
                    <BTable
                        :items="selectedFiles"
                        :fields="tableFields"
                        primary-key="name"
                        hover
                        striped
                        small
                        fixed
                        show-empty
                        thead-class="file-table-header">
                        <template v-slot:cell(name)="{ item }">
                            <BFormInput v-model="item.name" size="sm" :placeholder="item.file.name" />
                        </template>

                        <template v-slot:head(extension)>
                            <div class="d-flex align-items-center column-header">
                                <span class="column-label">Type</span>
                                <BFormSelect
                                    v-model="bulkExtension"
                                    v-b-tooltip.hover.noninteractive
                                    class="bulk-select"
                                    size="sm"
                                    title="Set file format for all files"
                                    :disabled="!configurationsReady"
                                    @change="setAllExtensions">
                                    <option :value="null">Set all...</option>
                                    <option
                                        v-for="(ext, extIndex) in effectiveExtensions"
                                        :key="extIndex"
                                        :value="ext.id">
                                        {{ ext.text }}
                                    </option>
                                </BFormSelect>
                                <FontAwesomeIcon
                                    v-if="bulkExtensionWarning"
                                    v-b-tooltip.hover.noninteractive
                                    class="text-warning ml-1"
                                    :icon="faExclamationTriangle"
                                    :title="bulkExtensionWarning" />
                            </div>
                        </template>

                        <template v-slot:cell(extension)="{ item }">
                            <BFormSelect v-model="item.extension" size="sm" :disabled="!configurationsReady">
                                <option v-for="(ext, extIndex) in effectiveExtensions" :key="extIndex" :value="ext.id">
                                    {{ ext.text }}
                                </option>
                            </BFormSelect>
                        </template>

                        <template v-slot:head(dbKey)>
                            <div class="d-flex align-items-center column-header">
                                <span class="column-label">Database</span>
                                <BFormSelect
                                    v-model="bulkDbKey"
                                    v-b-tooltip.hover.noninteractive
                                    class="bulk-select"
                                    size="sm"
                                    title="Set database key for all files"
                                    :disabled="!configurationsReady"
                                    @change="setAllDbKeys">
                                    <option :value="null">Set all...</option>
                                    <option
                                        v-for="(dbKey, dbKeyIndex) in listDbKeys"
                                        :key="dbKeyIndex"
                                        :value="dbKey.id">
                                        {{ dbKey.text }}
                                    </option>
                                </BFormSelect>
                            </div>
                        </template>

                        <template v-slot:cell(dbKey)="{ item }">
                            <BFormSelect v-model="item.dbKey" size="sm" :disabled="!configurationsReady">
                                <option v-for="(dbKey, dbKeyIndex) in listDbKeys" :key="dbKeyIndex" :value="dbKey.id">
                                    {{ dbKey.text }}
                                </option>
                            </BFormSelect>
                        </template>

                        <template v-slot:cell(size)="{ item }">
                            {{ bytesToString(item.file.size) }}
                        </template>

                        <template v-slot:cell(options)="{ item }">
                            <div class="d-flex flex-column">
                                <BFormCheckbox v-model="item.spaceToTab" size="sm" class="mb-1">
                                    Spaces→Tabs
                                </BFormCheckbox>
                                <BFormCheckbox v-model="item.toPosixLines" size="sm"> POSIX </BFormCheckbox>
                            </div>
                        </template>

                        <template v-slot:cell(actions)="{ index }">
                            <button class="btn btn-link text-danger p-0" @click="removeFile(index)">
                                <FontAwesomeIcon :icon="faTimes" />
                            </button>
                        </template>
                    </BTable>
                </div>

                <div class="file-list-actions mt-2">
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
    margin-bottom: 0.5rem;
}

.file-table-container {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;

    :deep(.file-table-header) {
        position: sticky;
        top: 0;
        background-color: $white;
        z-index: 1;
    }

    :deep(.file-name-cell) {
        min-width: 200px;
    }

    .column-header {
        gap: 0.5rem;

        .column-label {
            font-weight: 600;
            white-space: nowrap;
        }

        .bulk-select {
            flex: 1;
            min-width: 0;
        }
    }
}

.file-list-actions {
    flex-shrink: 0;
    display: flex;
    gap: 0.5rem;
    justify-content: flex-start;
    padding-top: 1rem;
    border-top: 1px solid $border-color;
}
</style>
