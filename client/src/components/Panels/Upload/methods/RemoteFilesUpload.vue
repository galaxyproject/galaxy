<script setup lang="ts">
import { faFolder, faPlus, faTimes, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BFormCheckbox, BFormInput, BPagination, BTable } from "bootstrap-vue";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { browseRemoteFiles, fetchFileSources, type RemoteEntry } from "@/api/remoteFiles";
import type { BreadcrumbItem } from "@/components/Common";
import { Model } from "@/components/FilesDialog/model";
import { fileSourcePluginToItem } from "@/components/FilesDialog/utilities";
import type { SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import { useBulkUploadOperations } from "@/composables/upload/bulkUploadOperations";
import { useCollectionCreation } from "@/composables/upload/collectionCreation";
import { useUploadDefaults } from "@/composables/upload/uploadDefaults";
import { useUploadItemValidation } from "@/composables/upload/uploadItemValidation";
import { useUploadReadyState } from "@/composables/upload/uploadReadyState";
import { useUploadQueue } from "@/composables/uploadQueue";
import { useUrlTracker } from "@/composables/urlTracker";
import { errorMessageAsString } from "@/utils/simple-error";
import { mapToRemoteFileUpload } from "@/utils/upload/itemMappers";
import { USER_FILE_PREFIX } from "@/utils/url";
import { bytesToString } from "@/utils/utils";

import type { UploadMethodComponent, UploadMethodConfig } from "../types";
import type { RemoteFileItem } from "../types/uploadItem";

import CollectionCreationConfig from "../CollectionCreationConfig.vue";
import RemoteEntryMetadata from "../shared/RemoteEntryMetadata.vue";
import UploadTableBulkDbKeyHeader from "../shared/UploadTableBulkDbKeyHeader.vue";
import UploadTableBulkExtensionHeader from "../shared/UploadTableBulkExtensionHeader.vue";
import UploadTableDbKeyCell from "../shared/UploadTableDbKeyCell.vue";
import UploadTableExtensionCell from "../shared/UploadTableExtensionCell.vue";
import UploadTableNameCell from "../shared/UploadTableNameCell.vue";
import UploadTableOptionsCell from "../shared/UploadTableOptionsCell.vue";
import UploadTableOptionsHeader from "../shared/UploadTableOptionsHeader.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbNavigation from "@/components/Common/BreadcrumbNavigation.vue";
import DataDialogSearch from "@/components/SelectionDialog/DataDialogSearch.vue";

interface Props {
    method: UploadMethodConfig;
    targetHistoryId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "ready", ready: boolean): void;
}>();

const uploadQueue = useUploadQueue();
const router = useRouter();

const { effectiveExtensions, listDbKeys, configurationsReady, createItemDefaults } = useUploadDefaults();

const tableContainerRef = ref<HTMLElement | null>(null);
const collectionConfigComponent = ref<InstanceType<typeof CollectionCreationConfig> | null>(null);

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

const showBrowser = ref(true);
const remoteFileItems = ref<RemoteFileItem[]>([]);

const selectionModel = ref<Model>(new Model({ multiple: true }));
const selectionCount = ref(0);
const urlTracker = useUrlTracker<SelectionItem>();
const browserItems = ref<SelectionItem[]>([]);
const searchQuery = ref("");
const isBusy = ref(false);
const errorMessage = ref<string>();
const currentPage = ref(1);
const perPage = ref(25);
const totalMatches = ref(0);

/**
 * Sequence id to track latest load request. Incremented on each navigation/load.
 */
const loadSequenceId = ref(0);

async function executeIfLatest<T>(
    operation: () => Promise<T>,
    onSuccess: (data: T) => void,
    onError?: (error: unknown) => void,
): Promise<void> {
    const seq = loadSequenceId.value;
    isBusy.value = true;
    errorMessage.value = undefined;

    try {
        const result = await operation();
        // Ignore if a newer load started while we were fetching
        if (seq === loadSequenceId.value) {
            onSuccess(result);
        }
    } catch (error) {
        if (seq === loadSequenceId.value) {
            if (onError) {
                onError(error);
            } else {
                errorMessage.value = errorMessageAsString(error);
            }
        }
    } finally {
        if (seq === loadSequenceId.value) {
            isBusy.value = false;
        }
    }
}

const hasItems = computed(() => remoteFileItems.value.length > 0);
const hasSelection = computed(() => selectionCount.value > 0);

const breadcrumbs = computed(() => {
    const crumbs: BreadcrumbItem[] = [{ title: "Sources", index: -1 }];
    urlTracker.navigationHistory.value.forEach((item, index) => {
        crumbs.push({ title: item.label, index });
    });
    return crumbs;
});

const { isNameValid, restoreOriginalName } = useUploadItemValidation();

const bulk = useBulkUploadOperations(remoteFileItems, effectiveExtensions);

const { isReadyToUpload } = useUploadReadyState(hasItems, collectionState);

watch(isReadyToUpload, (ready) => emit("ready", ready), { immediate: true });

function entryToSelectionItem(entry: RemoteEntry): SelectionItem {
    return {
        id: entry.uri,
        label: entry.name,
        url: entry.uri,
        isLeaf: entry.class === "File",
        details: entry.class === "File" ? entry.ctime : "",
        entry: entry,
    };
}

/**
 * Comparator for sorting file sources.
 * User-created sources come first, then alphabetical by label.
 */
function sortFileSources(a: SelectionItem, b: SelectionItem): number {
    const aIsUser = a.url.startsWith(USER_FILE_PREFIX);
    const bIsUser = b.url.startsWith(USER_FILE_PREFIX);

    if (aIsUser && !bIsUser) {
        return -1;
    }
    if (!aIsUser && bIsUser) {
        return 1;
    }
    return a.label.localeCompare(b.label);
}

async function loadFileSources() {
    await executeIfLatest(
        () => fetchFileSources(),
        (sources) => {
            let items = sources.map(fileSourcePluginToItem);
            items = items.sort(sortFileSources);

            // Apply search filter if present
            if (searchQuery.value) {
                const query = searchQuery.value.toLowerCase();
                items = items.filter((item) => item.label.toLowerCase().includes(query));
            }

            browserItems.value = items;
        },
    );
}

async function loadDirectory(uri: string) {
    const offset = (currentPage.value - 1) * perPage.value;
    await executeIfLatest(
        () => browseRemoteFiles(uri, false, false, perPage.value, offset, searchQuery.value || undefined),
        (result) => {
            browserItems.value = result.entries.map(entryToSelectionItem);
            totalMatches.value = result.totalMatches;
        },
        (error) => {
            browserItems.value = [];
            totalMatches.value = 0;
            errorMessage.value = errorMessageAsString(error);
        },
    );
}

async function load() {
    // Bump sequence id so any in-flight requests are considered stale
    loadSequenceId.value += 1;
    if (urlTracker.isAtRoot.value) {
        await loadFileSources();
    } else if (urlTracker.current.value) {
        await loadDirectory(urlTracker.current.value.url);
    }
}

function onItemClick(item: SelectionItem) {
    // Don't allow navigation or selection while loading or if there's an error
    if (isBusy.value || errorMessage.value) {
        return;
    }

    if (!item.isLeaf) {
        // Navigate into directory
        open(item);
    } else {
        // Toggle file selection
        selectionModel.value.add(item);
        selectionCount.value = selectionModel.value.count();
    }
}

function open(item: SelectionItem) {
    urlTracker.forward(item);
    currentPage.value = 1;
    clearSearch();
    load();
}

function navigateToBreadcrumb(index: number) {
    // Navigate to a specific breadcrumb by resetting navigation to that point
    if (index === -1) {
        // Navigate to root
        urlTracker.reset();
    } else {
        // Navigate to specific index in history
        const targetDepth = index + 1;
        const currentDepth = urlTracker.navigationHistory.value.length;
        const stepsBack = currentDepth - targetDepth;

        for (let i = 0; i < stepsBack; i++) {
            urlTracker.backward();
        }
    }
    currentPage.value = 1;
    clearSearch();
    load();
}

function toggleFileSelection(item: SelectionItem) {
    if (item.isLeaf) {
        selectionModel.value.add(item);
        selectionCount.value = selectionModel.value.count();
    }
}

function isSelected(item: SelectionItem): boolean {
    return selectionModel.value.exists(item.id);
}

function addSelectedFiles() {
    const selectedItems = selectionModel.value.finalize() as SelectionItem[];

    // Filter out any items that already exist in remoteFileItems
    const existingUrls = new Set(remoteFileItems.value.map((item) => item.url));
    const newItems = selectedItems.filter((item) => !existingUrls.has(item.url));

    // Add new items
    for (const item of newItems) {
        remoteFileItems.value.push(createRemoteFileItem(nextId++, item));
    }

    // Clear selection and switch to table view
    selectionModel.value = new Model({ multiple: true });
    selectionCount.value = 0;
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

function createNewFileSource() {
    router.push("/file_source_instances/create");
}

// Browser table fields
const browserFields = [
    {
        key: "select",
        label: "",
        thStyle: { width: "40px" },
        tdClass: "align-middle",
    },
    {
        key: "user",
        label: "",
        sortable: false,
        thStyle: { width: "35px" },
        tdClass: "align-middle text-center",
    },
    {
        key: "name",
        label: "Name",
        sortable: false,
        thStyle: { minWidth: "200px" },
        tdClass: "align-middle",
    },
    {
        key: "details",
        label: "Details",
        sortable: false,
        thStyle: { width: "auto", minWidth: "200px" },
        tdClass: "align-middle",
    },
];

// File list table fields
const tableFields = [
    {
        key: "name",
        label: "Name",
        sortable: true,
        thStyle: { width: "200px" },
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
        key: "url",
        label: "URI",
        sortable: false,
        thStyle: { width: "auto" },
        tdClass: "align-middle uri-column",
    },
    {
        key: "extension",
        label: "Type",
        sortable: false,
        thStyle: { minWidth: "180px", width: "180px" },
        tdClass: "align-middle",
    },
    {
        key: "dbKey",
        label: "Reference",
        sortable: false,
        thStyle: { minWidth: "200px", width: "200px" },
        tdClass: "align-middle",
    },
    {
        key: "options",
        label: "Upload Settings",
        sortable: false,
        thStyle: { width: "auto" },
        tdClass: "align-middle",
    },
    { key: "actions", label: "", sortable: false, tdClass: "text-right align-middle", thStyle: { width: "50px" } },
];

function clearAll() {
    remoteFileItems.value = [];
    showBrowser.value = true;
    resetCollection();
    selectionModel.value = new Model({ multiple: true });
    selectionCount.value = 0;
    clearSearch();
    urlTracker.reset();
}

function clearSearch() {
    searchQuery.value = "";
}

function startUpload() {
    const uploads = remoteFileItems.value.map((item) => mapToRemoteFileUpload(item, props.targetHistoryId));
    const collectionConfig = buildCollectionConfig(props.targetHistoryId);

    uploadQueue.enqueue(uploads, collectionConfig);

    // Reset state
    remoteFileItems.value = [];
    showBrowser.value = true;
    resetCollection();
    selectionModel.value = new Model({ multiple: true });
    selectionCount.value = 0;
    clearSearch();
    urlTracker.reset();
}

onMounted(() => {
    load();
});

watch(searchQuery, () => {
    currentPage.value = 1;
    load();
});

watch(currentPage, () => {
    if (!urlTracker.isAtRoot.value) {
        load();
    }
});

function onErrorRetry() {
    errorMessage.value = undefined;
    currentPage.value = 1;
    clearSearch();

    load();
}

defineExpose<UploadMethodComponent>({ startUpload });
</script>

<template>
    <div class="remote-files-upload">
        <!-- File Browser Phase -->
        <div v-if="showBrowser" class="file-browser">
            <!-- Navigation breadcrumb -->
            <div class="browser-header mb-2">
                <BreadcrumbNavigation
                    v-if="!urlTracker.isAtRoot.value"
                    :items="breadcrumbs"
                    @navigate="navigateToBreadcrumb" />
                <span v-else class="font-weight-bold">Select a File Source</span>
            </div>

            <!-- Search bar -->
            <div class="search-bar-container mb-2">
                <DataDialogSearch
                    v-model="searchQuery"
                    :title="urlTracker.isAtRoot.value ? 'file sources' : 'files and folders'" />
            </div>

            <!-- Error message -->
            <BAlert v-if="errorMessage" variant="danger" show dismissible @dismissed="errorMessage = undefined">
                <div class="d-flex justify-content-between align-items-center">
                    <span>{{ errorMessage }}</span>
                    <GButton color="red" class="ml-2" @click="onErrorRetry"> Retry </GButton>
                </div>
            </BAlert>

            <!-- Browser table -->
            <div class="browser-table-container">
                <BTable
                    v-if="!errorMessage && (browserItems.length > 0 || isBusy)"
                    :items="browserItems"
                    :fields="browserFields"
                    :busy="isBusy"
                    hover
                    striped
                    small
                    fixed
                    thead-class="browser-table-header"
                    @row-clicked="onItemClick">
                    <!-- Select column (only for files) -->
                    <template v-slot:cell(select)="{ item }">
                        <BFormCheckbox
                            v-if="item.isLeaf"
                            :checked="isSelected(item)"
                            @change="toggleFileSelection(item)"
                            @click.stop />
                    </template>

                    <!-- User icon column (for user-created file sources) -->
                    <template v-slot:cell(user)="{ item }">
                        <FontAwesomeIcon
                            v-if="urlTracker.isAtRoot.value && !item.isLeaf && item.url.startsWith(USER_FILE_PREFIX)"
                            v-b-tooltip.hover.noninteractive
                            :icon="faUser"
                            class="text-primary"
                            fixed-width
                            title="User-created file source" />
                    </template>

                    <!-- Name column with icons -->
                    <template v-slot:cell(name)="{ item }">
                        <div class="d-flex align-items-center" :class="{ 'cursor-pointer': !item.isLeaf }">
                            <FontAwesomeIcon
                                v-if="!item.isLeaf"
                                :icon="faFolder"
                                class="mr-2 text-warning"
                                fixed-width />
                            <span>{{ item.label }}</span>
                        </div>
                    </template>

                    <!-- Details column -->
                    <template v-slot:cell(details)="{ item }">
                        <span v-if="urlTracker.isAtRoot && item.details">
                            {{ item.details }}
                        </span>
                        <RemoteEntryMetadata v-else-if="item.isLeaf && item.entry" :entry="item.entry" />
                    </template>

                    <!-- Loading slot -->
                    <template v-slot:table-busy>
                        <div class="text-center my-2">
                            <b-spinner small class="align-middle"></b-spinner>
                            <strong class="ml-2">Loading...</strong>
                        </div>
                    </template>
                </BTable>

                <!-- Empty state message when no items are available -->
                <div v-else-if="!errorMessage && !isBusy" class="text-center text-muted my-5">
                    <p v-if="searchQuery" class="lead">
                        No {{ urlTracker.isAtRoot.value ? "file sources" : "files or folders" }} match your search "{{
                            searchQuery
                        }}"
                    </p>
                    <p v-else-if="urlTracker.isAtRoot.value" class="lead">
                        No file sources available. Connect a new remote source to get started.
                    </p>
                    <p v-else class="lead">This directory is empty.</p>
                </div>
            </div>

            <!-- Pagination -->
            <div v-if="!urlTracker.isAtRoot.value && totalMatches > perPage" class="mt-2">
                <BPagination
                    v-model="currentPage"
                    :total-rows="totalMatches"
                    :per-page="perPage"
                    align="center"
                    size="sm" />
            </div>

            <!-- Action buttons -->
            <div class="browser-actions mt-3">
                <GButton v-if="urlTracker.isAtRoot.value" color="blue" @click="createNewFileSource">
                    <FontAwesomeIcon :icon="faPlus" class="mr-1" />
                    Connect New Remote Source
                </GButton>
                <GButton v-if="hasItems && !hasSelection" color="grey" outline @click="showFileList">
                    View Selected Files ({{ remoteFileItems.length }})
                </GButton>
                <GButton
                    v-if="!urlTracker.isAtRoot.value"
                    color="blue"
                    :disabled="!hasSelection"
                    class="ml-auto"
                    @click="addSelectedFiles">
                    <FontAwesomeIcon :icon="faPlus" class="mr-1" />
                    Add Selected Files ({{ selectionCount }})
                </GButton>
            </div>
        </div>

        <!-- File List Phase -->
        <div v-else class="file-list">
            <div class="file-list-header mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <span class="font-weight-bold">{{ remoteFileItems.length }} file(s) selected</span>
                </div>
            </div>

            <div ref="tableContainerRef" class="file-table-container">
                <BTable
                    :items="remoteFileItems"
                    :fields="tableFields"
                    hover
                    striped
                    small
                    fixed
                    thead-class="file-table-header">
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
                            :to-posix-lines="item.toPosixLines"
                            :deferred="item.deferred"
                            :show-deferred="true"
                            @updateSpaceToTab="item.spaceToTab = $event"
                            @updateToPosixLines="item.toPosixLines = $event"
                            @updateDeferred="item.deferred = $event" />
                    </template>

                    <!-- Actions column -->
                    <template v-slot:cell(actions)="{ item }">
                        <button
                            v-b-tooltip.hover.noninteractive
                            class="btn btn-link text-danger remove-btn"
                            title="Remove file from list"
                            @click="removeItem(item.id)">
                            <FontAwesomeIcon :icon="faTimes" />
                        </button>
                    </template>
                </BTable>
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
}

.browser-header {
    flex-shrink: 0;
    @include upload-list-header;
}

.search-bar-container {
    flex-shrink: 0;
}

.browser-table-container {
    flex: 1;
    overflow: auto;
    min-height: 0;

    :deep(.browser-table-header) {
        @include upload-table-header;
    }

    :deep(tbody tr) {
        cursor: pointer;

        &:hover {
            background-color: rgba($brand-primary, 0.05);
        }
    }
}

.browser-actions {
    flex-shrink: 0;
    display: flex;
    gap: 0.5rem;
    padding-top: 1rem;
    border-top: 1px solid $border-color;
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

    :deep(.file-table-header) {
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
