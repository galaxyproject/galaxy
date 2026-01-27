<script setup lang="ts">
import { faCloudUploadAlt, faLaptop, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BTable } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { useFileDrop } from "@/composables/fileDrop";
import { useBulkUploadOperations } from "@/composables/upload/bulkUploadOperations";
import { useCollectionCreation } from "@/composables/upload/collectionCreation";
import { useUploadAdvancedMode } from "@/composables/upload/uploadAdvancedMode";
import { useUploadDefaults } from "@/composables/upload/uploadDefaults";
import { useUploadItemValidation } from "@/composables/upload/uploadItemValidation";
import { useUploadReadyState } from "@/composables/upload/uploadReadyState";
import { useUploadStaging } from "@/composables/upload/useUploadStaging";
import { useUploadQueue } from "@/composables/uploadQueue";
import { mapToLocalFileUpload } from "@/utils/upload/itemMappers";
import { bytesToString } from "@/utils/utils";

import type { UploadMethodComponent, UploadMethodConfig } from "../types";
import type { LocalFileItem } from "../types/uploadItem";

import CollectionCreationConfig from "../CollectionCreationConfig.vue";
import UploadTableBulkDbKeyHeader from "../shared/UploadTableBulkDbKeyHeader.vue";
import UploadTableBulkExtensionHeader from "../shared/UploadTableBulkExtensionHeader.vue";
import UploadTableDbKeyCell from "../shared/UploadTableDbKeyCell.vue";
import UploadTableExtensionCell from "../shared/UploadTableExtensionCell.vue";
import UploadTableNameCell from "../shared/UploadTableNameCell.vue";
import UploadTableOptionsCell from "../shared/UploadTableOptionsCell.vue";
import UploadTableOptionsHeader from "../shared/UploadTableOptionsHeader.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    method: UploadMethodConfig;
    targetHistoryId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "ready", ready: boolean): void;
}>();

const { advancedMode } = useUploadAdvancedMode();

const uploadQueue = useUploadQueue();

const { effectiveExtensions, listDbKeys, configurationsReady, createItemDefaults } = useUploadDefaults();

const selectedFiles = ref<LocalFileItem[]>([]);
const { clear: clearStaging } = useUploadStaging<LocalFileItem>(props.method.id, selectedFiles);
const uploadFile = ref<HTMLInputElement | null>(null);
const dropZoneElement = ref<HTMLElement | null>(null);
const collectionConfigComponent = ref<InstanceType<typeof CollectionCreationConfig> | null>(null);

const { collectionState, handleCollectionStateChange, buildCollectionConfig, resetCollection } =
    useCollectionCreation(collectionConfigComponent);

const hasFiles = computed(() => selectedFiles.value.length > 0);
const totalSize = computed(() => {
    const bytes = selectedFiles.value.reduce((sum, item) => sum + item.file.size, 0);
    return bytesToString(bytes);
});

const { isNameValid, restoreOriginalName } = useUploadItemValidation();

const bulk = useBulkUploadOperations(selectedFiles, effectiveExtensions);

const { isReadyToUpload } = useUploadReadyState(hasFiles, collectionState);

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

watch(isReadyToUpload, (ready) => emit("ready", ready), { immediate: true });

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
    const defaults = createItemDefaults();

    for (const file of fileArray) {
        selectedFiles.value.push({
            file,
            name: file.name,
            size: file.size,
            ...defaults,
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
    resetCollection();
}

function startUpload() {
    const uploads = selectedFiles.value.map((item) => mapToLocalFileUpload(item, props.targetHistoryId));
    const collectionConfig = buildCollectionConfig(props.targetHistoryId);

    uploadQueue.enqueue(uploads, collectionConfig);
    selectedFiles.value = [];
    clearStaging();
    resetCollection();
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
                        <template v-slot:cell(name)="{ item }">
                            <UploadTableNameCell
                                :value="item.name"
                                :state="isNameValid(item.name)"
                                tooltip="Dataset name in your history (required)"
                                @input="item.name = $event"
                                @blur="restoreOriginalName(item, item.file.name)" />
                        </template>

                        <template v-slot:cell(size)="{ item }">
                            {{ bytesToString(item.size) }}
                        </template>

                        <template v-slot:head(extension)>
                            <UploadTableBulkExtensionHeader
                                :value="bulk.bulkExtension.value"
                                :extensions="effectiveExtensions"
                                :warning="bulk.bulkExtensionWarning.value"
                                :disabled="!configurationsReady"
                                tooltip="Set file format for all files"
                                @input="bulk.setAllExtensions" />
                        </template>

                        <template v-slot:cell(extension)="{ item }">
                            <UploadTableExtensionCell
                                :value="item.extension"
                                :extensions="effectiveExtensions"
                                :warning="bulk.getExtensionWarning(item.extension)"
                                :disabled="!configurationsReady"
                                @input="item.extension = $event" />
                        </template>

                        <template v-slot:head(dbKey)>
                            <UploadTableBulkDbKeyHeader
                                :value="bulk.bulkDbKey.value"
                                :db-keys="listDbKeys"
                                :disabled="!configurationsReady"
                                tooltip="Set database key for all files"
                                @input="bulk.setAllDbKeys" />
                        </template>

                        <template v-slot:cell(dbKey)="{ item }">
                            <UploadTableDbKeyCell
                                :value="item.dbkey"
                                :db-keys="listDbKeys"
                                :disabled="!configurationsReady"
                                @input="item.dbkey = $event" />
                        </template>

                        <template v-slot:head(options)>
                            <UploadTableOptionsHeader
                                :all-space-to-tab="bulk.allSpaceToTab.value"
                                :space-to-tab-indeterminate="bulk.spaceToTabIndeterminate.value"
                                :show-posix="advancedMode"
                                :all-to-posix-lines="bulk.allToPosixLines.value"
                                :to-posix-lines-indeterminate="bulk.toPosixLinesIndeterminate.value"
                                @toggle-space-to-tab="bulk.toggleAllSpaceToTab"
                                @toggle-to-posix-lines="bulk.toggleAllToPosixLines" />
                        </template>

                        <template v-slot:cell(options)="{ item }">
                            <UploadTableOptionsCell
                                :space-to-tab="item.spaceToTab"
                                :show-posix="advancedMode"
                                :to-posix-lines="item.toPosixLines"
                                @updateSpaceToTab="item.spaceToTab = $event"
                                @updateToPosixLines="item.toPosixLines = $event" />
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

                <!-- Collection Creation Section -->
                <CollectionCreationConfig
                    ref="collectionConfigComponent"
                    :files="selectedFiles"
                    @update:state="handleCollectionStateChange" />

                <div class="file-list-actions mt-2">
                    <GButton
                        color="grey"
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
@import "../shared/upload-table-shared.scss";

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
    @include upload-list-header;
}

.file-table-container {
    @include upload-table-container;

    :deep(.file-table-header) {
        @include upload-table-header;
    }

    :deep(.file-name-cell) {
        min-width: 200px;
    }
}

.file-list-actions {
    @include upload-list-actions;
}
</style>
