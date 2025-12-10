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
    size: number;
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

const bulkExtension = ref<string | null>(null);
const bulkDbKey = ref<string | null>(null);

const bulkExtensionWarning = computed(() => {
    if (!bulkExtension.value) {
        return null;
    }
    const ext = findExtension(effectiveExtensions.value, bulkExtension.value);
    return ext?.upload_warning || null;
});

function getExtensionWarning(extensionId: string): string | null {
    const ext = findExtension(effectiveExtensions.value, extensionId);
    return ext?.upload_warning || null;
}

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

const allSpaceToTab = computed(() => selectedFiles.value.length > 0 && selectedFiles.value.every((f) => f.spaceToTab));

const allToPosixLines = computed(
    () => selectedFiles.value.length > 0 && selectedFiles.value.every((f) => f.toPosixLines),
);

const spaceToTabIndeterminate = computed(
    () =>
        selectedFiles.value.length > 0 &&
        selectedFiles.value.some((f) => f.spaceToTab) &&
        !selectedFiles.value.every((f) => f.spaceToTab),
);

const toPosixLinesIndeterminate = computed(
    () =>
        selectedFiles.value.length > 0 &&
        selectedFiles.value.some((f) => f.toPosixLines) &&
        !selectedFiles.value.every((f) => f.toPosixLines),
);

function toggleAllSpaceToTab() {
    const newValue = !allSpaceToTab.value;
    selectedFiles.value.forEach((f) => (f.spaceToTab = newValue));
}

function toggleAllToPosixLines() {
    const newValue = !allToPosixLines.value;
    selectedFiles.value.forEach((f) => (f.toPosixLines = newValue));
}

function restoreOriginalName(item: FileWithMetadata) {
    if (!item.name.trim()) {
        item.name = item.file.name;
    }
}

function isNameValid(name: string): boolean | null {
    return name.trim().length > 0 ? null : false;
}

const tableFields = [
    {
        key: "name",
        label: "Name",
        sortable: true,
        thStyle: { minWidth: "200px", width: "auto" },
        tdClass: "file-name-cell align-middle",
    },
    {
        key: "size",
        label: "Size",
        sortable: true,
        thStyle: { minWidth: "80px", width: "80px" },
        tdClass: "align-middle",
    },
    {
        key: "extension",
        label: "Type",
        sortable: false,
        thStyle: { minWidth: "100px", width: "180px" },
        tdClass: "align-middle",
    },
    {
        key: "dbKey",
        label: "Reference",
        sortable: false,
        thStyle: { minWidth: "100px", width: "200px" },
        tdClass: "align-middle",
    },
    {
        key: "options",
        label: "Upload Settings",
        sortable: false,
        thStyle: { width: "140px" },
        tdClass: "align-middle",
    },
    { key: "actions", label: "", sortable: false, tdClass: "text-right align-middle", thStyle: { width: "50px" } },
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
            size: file.size,
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
            tabindex="0"
            class="drop-zone"
            data-galaxy-file-drop-target
            :class="{ 'drop-zone-active': isFileOverDropZone, 'has-files': hasFiles }">
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
                        hover
                        striped
                        small
                        fixed
                        thead-class="file-table-header">
                        <template v-slot:cell(name)="{ item, index }">
                            <BFormInput
                                :key="`name-${index}`"
                                v-model="item.name"
                                v-b-tooltip.hover.noninteractive
                                size="sm"
                                :state="isNameValid(item.name)"
                                title="Dataset name in your history (required)"
                                @blur="restoreOriginalName(item)" />
                        </template>

                        <template v-slot:cell(size)="{ item }">
                            {{ bytesToString(item.size) }}
                        </template>

                        <template v-slot:head(extension)>
                            <div class="column-header-vertical">
                                <span class="column-title">Type</span>
                                <BFormSelect
                                    v-model="bulkExtension"
                                    v-b-tooltip.hover.noninteractive
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
                                    class="text-warning warning-icon"
                                    :icon="faExclamationTriangle"
                                    :title="bulkExtensionWarning" />
                            </div>
                        </template>

                        <template v-slot:cell(extension)="{ item }">
                            <div class="d-flex align-items-center">
                                <BFormSelect
                                    v-model="item.extension"
                                    v-b-tooltip.hover.noninteractive
                                    size="sm"
                                    title="File format (auto-detect recommended)"
                                    :disabled="!configurationsReady">
                                    <option
                                        v-for="(ext, extIndex) in effectiveExtensions"
                                        :key="extIndex"
                                        :value="ext.id">
                                        {{ ext.text }}
                                    </option>
                                </BFormSelect>
                                <FontAwesomeIcon
                                    v-if="getExtensionWarning(item.extension)"
                                    v-b-tooltip.hover.noninteractive
                                    class="text-warning ml-1 flex-shrink-0"
                                    :icon="faExclamationTriangle"
                                    :title="getExtensionWarning(item.extension)" />
                            </div>
                        </template>

                        <template v-slot:head(dbKey)>
                            <div class="column-header-vertical">
                                <span class="column-title">Reference</span>
                                <BFormSelect
                                    v-model="bulkDbKey"
                                    v-b-tooltip.hover.noninteractive
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
                            <BFormSelect
                                v-model="item.dbKey"
                                v-b-tooltip.hover.noninteractive
                                size="sm"
                                title="Database key for this dataset"
                                :disabled="!configurationsReady">
                                <option v-for="(dbKey, dbKeyIndex) in listDbKeys" :key="dbKeyIndex" :value="dbKey.id">
                                    {{ dbKey.text }}
                                </option>
                            </BFormSelect>
                        </template>

                        <template v-slot:head(options)>
                            <div class="options-header">
                                <span class="options-title">Upload Settings</span>
                                <div class="d-flex align-items-center">
                                    <BFormCheckbox
                                        v-b-tooltip.hover.noninteractive
                                        :checked="allSpaceToTab"
                                        :indeterminate="spaceToTabIndeterminate"
                                        size="sm"
                                        class="mr-2"
                                        title="Toggle all: Convert spaces to tab characters"
                                        @change="toggleAllSpaceToTab">
                                        <span class="small">Spaces→Tabs</span>
                                    </BFormCheckbox>
                                    <BFormCheckbox
                                        v-b-tooltip.hover.noninteractive
                                        :checked="allToPosixLines"
                                        :indeterminate="toPosixLinesIndeterminate"
                                        size="sm"
                                        title="Toggle all: Convert line endings to POSIX standard"
                                        @change="toggleAllToPosixLines">
                                        <span class="small">POSIX</span>
                                    </BFormCheckbox>
                                </div>
                            </div>
                        </template>

                        <template v-slot:cell(options)="{ item }">
                            <div class="d-flex align-items-center">
                                <BFormCheckbox
                                    v-model="item.spaceToTab"
                                    v-b-tooltip.hover.noninteractive
                                    size="sm"
                                    class="mr-2"
                                    title="Convert spaces to tab characters">
                                    <span class="small">Spaces→Tabs</span>
                                </BFormCheckbox>
                                <BFormCheckbox
                                    v-model="item.toPosixLines"
                                    v-b-tooltip.hover.noninteractive
                                    size="sm"
                                    title="Convert line endings to POSIX standard">
                                    <span class="small">POSIX</span>
                                </BFormCheckbox>
                            </div>
                        </template>

                        <template v-slot:cell(actions)="{ index }">
                            <button
                                v-b-tooltip.hover.noninteractive
                                class="btn btn-link text-danger remove-btn"
                                title="Remove file from list"
                                @click="removeFile(index)">
                                <FontAwesomeIcon :icon="faTimes" />
                            </button>
                        </template>
                    </BTable>
                </div>

                <div class="file-list-actions mt-2">
                    <GButton
                        color="blue"
                        tooltip
                        tooltip-placement="top"
                        title="Browse and add more files to the upload list"
                        @click="handleBrowse">
                        <FontAwesomeIcon :icon="faLaptop" class="mr-1" />
                        Add More Files
                    </GButton>
                    <GButton
                        outline
                        color="grey"
                        tooltip
                        tooltip-placement="top"
                        title="Remove all files from the upload list"
                        @click="clearAll">
                        Clear All
                    </GButton>
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
}

.file-table-container {
    flex: 1;
    min-height: 0;
    overflow: auto;

    :deep(.table) {
        table-layout: auto;
        min-width: 100%;
    }

    :deep(.file-table-header) {
        position: sticky;
        top: 0;
        background-color: $white;
        z-index: 100;

        th {
            vertical-align: middle;
            white-space: nowrap;
        }
    }

    :deep(.file-name-cell) {
        min-width: 200px;
    }

    .column-header-vertical {
        display: flex;
        flex-direction: column;
        align-items: stretch;
        position: relative;

        .column-title {
            font-weight: 600;
            margin-bottom: 0.25rem;
        }

        .warning-icon {
            position: absolute;
            right: 0;
            top: 0;
        }
    }

    .options-header {
        .options-title {
            display: block;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
    }

    .remove-btn {
        width: 30px;
        display: inline-flex;
        align-items: center;
        justify-content: center;

        &:hover {
            background-color: rgba($brand-danger, 0.1);
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
