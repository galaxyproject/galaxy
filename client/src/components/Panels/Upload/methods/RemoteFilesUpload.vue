<script setup lang="ts">
import { faPlus, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormInput } from "bootstrap-vue";
import { computed, nextTick, ref, watch } from "vue";

import type { RemoteEntry } from "@/api/remoteFiles";
import type { TableField } from "@/components/Common/GTable.types";
import type { SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import { useBulkUploadOperations } from "@/composables/upload/bulkUploadOperations";
import { useCollectionCreation } from "@/composables/upload/collectionCreation";
import { useUploadAdvancedMode } from "@/composables/upload/uploadAdvancedMode";
import { useUploadDefaults } from "@/composables/upload/uploadDefaults";
import { useUploadItemValidation } from "@/composables/upload/uploadItemValidation";
import { useUploadReadyState } from "@/composables/upload/uploadReadyState";
import { useUploadStaging } from "@/composables/upload/useUploadStaging";
import { useUploadQueue } from "@/composables/uploadQueue";
import { mapToRemoteFileUpload } from "@/utils/upload/itemMappers";
import { bytesToString } from "@/utils/utils";

import type { UploadMethodComponent, UploadMethodConfig } from "../types";
import type { RemoteFileItem } from "../types/uploadItem";

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
import RemoteFileBrowserContent from "@/components/FileBrowser/RemoteFileBrowserContent.vue";

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

const tableContainerRef = ref<HTMLElement | null>(null);
const collectionConfigComponent = ref<InstanceType<typeof CollectionCreationConfig> | null>(null);
const remoteFileItems = ref<RemoteFileItem[]>([]);
const { clear: clearStaging } = useUploadStaging<RemoteFileItem>(props.method.id, remoteFileItems);

const { collectionState, handleCollectionStateChange, buildCollectionConfig, resetCollection } =
    useCollectionCreation(collectionConfigComponent);

let nextId = 1;

function createRemoteFileItem(id: number, selectionItem: SelectionItem): RemoteFileItem {
    const entry = selectionItem.entry as RemoteEntry;
    const hashes = entry.class === "File" && entry.hashes ? entry.hashes : undefined;

    return {
        id,
        url: selectionItem.url,
        name: selectionItem.label,
        size: entry.class === "File" ? entry.size : 0,
        hashes,
        ...createItemDefaults(),
        deferred: false,
    };
}

const browserRef = ref<InstanceType<typeof RemoteFileBrowserContent> | null>(null);
const showBrowser = ref(true);

const hasItems = computed(() => remoteFileItems.value.length > 0);

const { isNameValid, restoreOriginalName } = useUploadItemValidation();

const bulk = useBulkUploadOperations(remoteFileItems, effectiveExtensions);

const { isReadyToUpload } = useUploadReadyState(hasItems, collectionState);

watch(isReadyToUpload, (ready) => emit("ready", ready), { immediate: true });

/**
 * Called when the user confirms a file selection in the browser.
 * Adds newly selected files to the upload list (deduplicating by URL) and switches to the list view.
 */
function onFilesConfirmed(items: SelectionItem[]) {
    const existingUrls = new Set(remoteFileItems.value.map((item) => item.url));
    const newItems = items.filter((item) => !existingUrls.has(item.url));

    for (const item of newItems) {
        remoteFileItems.value.push(createRemoteFileItem(nextId++, item));
    }

    showBrowser.value = false;
    scrollToBottom();
}

function showFileList() {
    showBrowser.value = false;
}

function showFileBrowser() {
    showBrowser.value = true;
}

function scrollToBottom() {
    nextTick(() => {
        if (tableContainerRef.value) {
            const container = tableContainerRef.value;
            container.scrollTop = container.scrollHeight;
        }
    });
}

function removeItem(id: number) {
    remoteFileItems.value = remoteFileItems.value.filter((item) => item.id !== id);
}

// File list table fields
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
        class: "size-column",
    },
    {
        key: "url",
        label: "URI",
        sortable: false,
        align: "center",
        class: "uri-column",
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

function clearAll() {
    remoteFileItems.value = [];
    resetCollection();
    browserRef.value?.reset();
    showBrowser.value = true;
}

function startUpload() {
    const uploads = remoteFileItems.value.map((item) => mapToRemoteFileUpload(item, props.targetHistoryId));
    const collectionConfig = buildCollectionConfig(props.targetHistoryId);

    uploadQueue.enqueue(uploads, collectionConfig);

    remoteFileItems.value = [];
    clearStaging();
    resetCollection();
    browserRef.value?.reset();
    showBrowser.value = true;
}

defineExpose<UploadMethodComponent>({ startUpload });
</script>

<template>
    <div class="remote-files-upload">
        <!-- File Browser Phase -->
        <div v-if="showBrowser" class="file-browser">
            <div v-if="hasItems" class="browser-staged-notice mb-2">
                <GButton size="small" color="grey" outline @click="showFileList">
                    View {{ remoteFileItems.length }} staged file(s)
                </GButton>
            </div>
            <RemoteFileBrowserContent
                ref="browserRef"
                :multiple="true"
                mode="file"
                ok-text="Add Selected Files"
                @confirm="onFilesConfirmed" />
        </div>

        <!-- File List Phase -->
        <div v-else class="file-list">
            <div class="file-list-header mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <span class="font-weight-bold">{{ remoteFileItems.length }} file(s) selected</span>
                </div>
            </div>

            <div ref="tableContainerRef" class="file-table-container">
                <GTable :items="remoteFileItems" :fields="tableFields" hover striped table-class="table-sm file-table">
                    <!-- Name column -->
                    <template v-slot:cell(name)="{ item }">
                        <UploadTableNameCell
                            :value="item.name"
                            :state="isNameValid(item.name)"
                            @input="item.name = $event"
                            @blur="restoreOriginalName(item, item.name)" />
                    </template>

                    <!-- Size column -->
                    <template v-slot:cell(size)="{ item }">
                        {{ bytesToString(item.size) }}
                    </template>

                    <!-- URL column (read-only) -->
                    <template v-slot:cell(url)="{ item }">
                        <div class="d-flex align-items-center">
                            <BFormInput :value="item.url" size="sm" readonly class="uri-input" />
                        </div>
                    </template>

                    <!-- Extension column with bulk operations -->
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

                    <!-- DbKey column with bulk operations -->
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

                    <!-- Options column with bulk checkboxes -->
                    <template v-slot:head(options)>
                        <UploadTableOptionsHeader
                            :all-space-to-tab="bulk.allSpaceToTab.value"
                            :space-to-tab-indeterminate="bulk.spaceToTabIndeterminate.value"
                            :show-posix="advancedMode"
                            :all-to-posix-lines="bulk.allToPosixLines.value"
                            :to-posix-lines-indeterminate="bulk.toPosixLinesIndeterminate.value"
                            :show-deferred="true"
                            :all-deferred="bulk.allDeferred.value"
                            :deferred-indeterminate="bulk.deferredIndeterminate.value"
                            @toggle-space-to-tab="bulk.toggleAllSpaceToTab"
                            @toggle-to-posix-lines="bulk.toggleAllToPosixLines"
                            @toggle-deferred="bulk.toggleAllDeferred" />
                    </template>

                    <template v-slot:cell(options)="{ item }">
                        <UploadTableOptionsCell
                            :space-to-tab="item.spaceToTab"
                            :show-posix="advancedMode"
                            :to-posix-lines="item.toPosixLines"
                            :show-deferred="true"
                            :deferred="item.deferred"
                            @updateSpaceToTab="item.spaceToTab = $event"
                            @updateToPosixLines="item.toPosixLines = $event"
                            @updateDeferred="item.deferred = $event" />
                    </template>

                    <!-- Actions column -->
                    <template v-slot:cell(actions)="{ item }">
                        <GButton
                            v-b-tooltip.hover.noninteractive
                            class="remove-btn"
                            color="red"
                            outline
                            transparent
                            title="Remove file from list"
                            @click="removeItem(item.id)">
                            <FontAwesomeIcon :icon="faTimes" />
                        </GButton>
                    </template>
                </GTable>
            </div>

            <!-- Collection Creation Section -->
            <CollectionCreationConfig
                ref="collectionConfigComponent"
                :files="remoteFileItems"
                @update:state="handleCollectionStateChange" />

            <div class="file-list-actions mt-2">
                <GButton
                    color="grey"
                    tooltip
                    tooltip-placement="top"
                    title="Add more remote files to the upload list"
                    @click="showFileBrowser">
                    <FontAwesomeIcon :icon="faPlus" class="mr-1" />
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
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";
@import "../shared/upload-table-shared.scss";

.remote-files-upload {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.file-browser {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;

    .browser-staged-notice {
        flex-shrink: 0;
    }
}
.file-list {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
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

    :deep(.uri-column) {
        width: 100%;
        max-width: 400px;
        overflow: hidden;

        .uri-input {
            font-family: monospace;
            font-size: 0.85rem;
            background-color: $gray-200;
        }
    }
}

.file-list-actions {
    @include upload-list-actions;
}

.cursor-pointer {
    cursor: pointer;
}
</style>
