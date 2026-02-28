<script setup lang="ts">
import { faCloudUploadAlt, faLaptop, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import { useFileDrop } from "@/composables/fileDrop";
import { useBulkUploadOperations } from "@/composables/upload/bulkUploadOperations";
import { useCollectionCreation } from "@/composables/upload/collectionCreation";
import { useUploadAdvancedMode } from "@/composables/upload/uploadAdvancedMode";
import { useUploadDefaults } from "@/composables/upload/uploadDefaults";
import { useUploadItemValidation } from "@/composables/upload/uploadItemValidation";
import { useUploadReadyState } from "@/composables/upload/uploadReadyState";
import { useUploadStaging } from "@/composables/upload/useUploadStaging";
import { buildPreparedUpload } from "@/utils/upload";
import { mapToLocalFileUpload } from "@/utils/upload/itemMappers";
import { bytesToString } from "@/utils/utils";

import type { PreparedUpload, UploadMethodComponent, UploadMethodConfig } from "../types";
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
import GTable from "@/components/Common/GTable.vue";

interface Props {
    method: UploadMethodConfig;
    /** History ID where uploaded datasets will be added. */
    targetHistoryId: string;
    /** Allow creating dataset collections from selected files. */
    allowCollections?: boolean;
    /** Optional list of allowed formats to constrain selectable extensions. */
    formats?: string[];
    /** When false, restrict selection to a single file. */
    multiple?: boolean;
    /** When true, do not persist staging to the shared store (modal use). */
    transient?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    allowCollections: true,
    formats: undefined,
    multiple: true,
    transient: false,
});

const emit = defineEmits<{
    (e: "ready", ready: boolean): void;
}>();

const { advancedMode } = useUploadAdvancedMode();

const { effectiveExtensions, listDbKeys, configurationsReady, createItemDefaults } = useUploadDefaults(props.formats);

const selectedFiles = ref<LocalFileItem[]>([]);
const { clear: clearStaging } = useUploadStaging<LocalFileItem>(props.method.id, selectedFiles, {
    disableStore: props.transient,
});
const uploadFile = ref<HTMLInputElement | null>(null);
const dropZoneElement = ref<HTMLElement | null>(null);
const collectionConfigComponent = ref<InstanceType<typeof CollectionCreationConfig> | null>(null);

const { buildCollectionConfig, collectionState, handleCollectionStateChange, resetCollection } =
    useCollectionCreation(collectionConfigComponent);

const hasFiles = computed(() => selectedFiles.value.length > 0);
const canAddMoreFiles = computed(() => props.multiple !== false || selectedFiles.value.length === 0);
const totalSize = computed(() => {
    const bytes = selectedFiles.value.reduce((sum, item) => sum + item.file.size, 0);
    return bytesToString(bytes);
});

const { isNameValid, restoreOriginalName } = useUploadItemValidation();

const bulk = useBulkUploadOperations(selectedFiles, effectiveExtensions);

const { isReadyToUpload } = useUploadReadyState(hasFiles, collectionState);

const showDragOverlay = computed(() => hasFiles.value && isFileOverDropZone.value);

const tableFields: TableField[] = [
    {
        key: "name",
        label: "Name",
        sortable: true,
        width: "200px",
        align: "center",
        class: "file-name-cell",
    },
    {
        key: "size",
        label: "Size",
        sortable: true,
        width: "80px",
        align: "center",
    },
    {
        key: "extension",
        label: "Type",
        sortable: false,
        width: "180px",
        align: "center",
    },
    {
        key: "dbKey",
        label: "Reference",
        sortable: false,
        width: "200px",
        align: "center",
    },
    {
        key: "options",
        label: "Upload Settings",
        sortable: false,
        width: "140px",
        align: "center",
    },
    {
        key: "actions",
        label: "",
        sortable: false,
        width: "50px",
        align: "center",
    },
];

watch(isReadyToUpload, (ready) => emit("ready", ready), { immediate: true });

function onDrop(evt: DragEvent) {
    if (evt.dataTransfer?.files) {
        addFiles(evt.dataTransfer.files);
    }
}

const { isFileOverDropZone } = useFileDrop({
    dropZone: dropZoneElement,
    onDrop,
    onDropCancel: () => {},
    solo: false,
    idleTime: 10000,
    ignoreChildrenOnLeave: true,
});

function addFiles(files: FileList | File[] | null) {
    if (!files) {
        return;
    }

    const fileArray = Array.from(files);
    const defaults = createItemDefaults();

    // Enforce single file limit if multiple is false
    const filesToAdd = props.multiple === false ? fileArray.slice(0, 1) : fileArray;

    for (const file of filesToAdd) {
        // If multiple is false, replace existing files
        if (props.multiple === false) {
            selectedFiles.value = [];
        }
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

function reset() {
    selectedFiles.value = [];
    resetCollection();
    clearStaging();
}

function prepareUpload(): PreparedUpload | null {
    if (selectedFiles.value.length === 0) {
        return null;
    }

    const uploads = selectedFiles.value.map((item) => mapToLocalFileUpload(item, props.targetHistoryId));
    return buildPreparedUpload(uploads, buildCollectionConfig(props.targetHistoryId));
}

defineExpose<UploadMethodComponent>({ prepareUpload, reset });
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
                    <GTable hover striped compact fixed :items="selectedFiles" :fields="tableFields" class="file-table">
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
                            <GButton
                                v-g-tooltip.hover.noninteractive
                                class="remove-btn"
                                color="red"
                                outline
                                transparent
                                title="Remove file from list"
                                @click="removeFile(index)">
                                <FontAwesomeIcon :icon="faTimes" />
                            </GButton>
                        </template>
                    </GTable>
                </div>

                <!-- Collection Creation Section -->
                <CollectionCreationConfig
                    v-if="props.allowCollections !== false"
                    ref="collectionConfigComponent"
                    :files="selectedFiles"
                    @update:state="handleCollectionStateChange" />

                <div class="file-list-actions mt-2">
                    <GButton
                        color="grey"
                        tooltip
                        tooltip-placement="top"
                        :disabled="!canAddMoreFiles"
                        :title="
                            canAddMoreFiles
                                ? 'Browse and add more files to the upload list'
                                : 'Only one file can be selected'
                        "
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
                        @click="reset">
                        Clear All
                    </GButton>
                </div>
            </div>

            <!-- Drag-over overlay -->
            <div v-show="showDragOverlay" class="drag-overlay">
                <div class="drag-overlay-content">
                    <FontAwesomeIcon :icon="faCloudUploadAlt" class="drag-overlay-icon" />
                    <p class="drag-overlay-text">Drop files to add them to the list</p>
                </div>
            </div>

            <!-- Hidden file input -->
            <label for="local-file-input" class="sr-only">Select files to upload</label>
            <input
                id="local-file-input"
                ref="uploadFile"
                type="file"
                :multiple="props.multiple !== false"
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
    position: relative;

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

    :deep(.file-table thead) {
        @include upload-table-header;
    }

    :deep(.file-name-cell) {
        min-width: 200px;
    }
}

.file-list-actions {
    @include upload-list-actions;
}

.drag-overlay {
    position: absolute;
    inset: 0;
    z-index: 101;
    pointer-events: none;
    background-color: rgba($brand-primary, 0.15);
    border: 2px solid $brand-primary;
    border-radius: $border-radius-large;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 1;
    transition: opacity 0.2s ease;

    &.v-leave-active {
        transition: opacity 0.1s ease;
    }
}

.drag-overlay-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    user-select: none;
}

.drag-overlay-icon {
    font-size: 3rem;
    color: $brand-primary;
    margin-bottom: 0.75rem;
    display: block;
}

.drag-overlay-text {
    font-size: 1.1rem;
    font-weight: 500;
    color: $brand-primary;
    margin: 0;
}
</style>
