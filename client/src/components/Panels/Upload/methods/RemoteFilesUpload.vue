<script setup lang="ts">
import { faFolder, faGlobe, faPlus, faTimes, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BFormCheckbox, BFormInput, BPagination } from "bootstrap-vue";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { browseRemoteFiles, fetchFileSources, type RemoteEntry } from "@/api/remoteFiles";
import type { BreadcrumbItem } from "@/components/Common";
import type { TableField } from "@/components/Common/GTable.types";
import { Model } from "@/components/FilesDialog/model";
import { fileSourcePluginToItem } from "@/components/FilesDialog/utilities";
import type { SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import { useFileSources } from "@/composables/fileSources";
import { useBulkUploadOperations } from "@/composables/upload/bulkUploadOperations";
import { useCollectionCreation } from "@/composables/upload/collectionCreation";
import { useUploadAdvancedMode } from "@/composables/upload/uploadAdvancedMode";
import { useUploadDefaults } from "@/composables/upload/uploadDefaults";
import { useUploadItemValidation } from "@/composables/upload/uploadItemValidation";
import { useUploadReadyState } from "@/composables/upload/uploadReadyState";
import { useUploadStaging } from "@/composables/upload/useUploadStaging";
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
import GTable from "@/components/Common/GTable.vue";
import DataDialogSearch from "@/components/SelectionDialog/DataDialogSearch.vue";

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
const router = useRouter();
const filesSources = useFileSources();

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

const showBrowser = ref(true);

const selectionModel = ref<Model>(new Model({ multiple: true }));
const selectionCount = ref(0);
const urlTracker = useUrlTracker<SelectionItem>();
const browserItems = ref<SelectionItem[]>([]);
const allFetchedItems = ref<SelectionItem[]>([]); // Store all items for client-side pagination
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

const currentFileSourceUri = computed(() => urlTracker.current.value?.url);

const supportsServerPagination = computed(() => filesSources.supportsPagination(currentFileSourceUri.value));

const supportsServerSearch = computed(() => filesSources.supportsSearch(currentFileSourceUri.value));

const hasPagination = computed(() => {
    if (urlTracker.isAtRoot.value || isBusy.value) {
        return false;
    }
    const itemCount = supportsServerPagination.value ? totalMatches.value : allFetchedItems.value.length;
    return itemCount > perPage.value;
});

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

const filesOnCurrentPage = computed(() => browserItems.value.filter((item) => item.isLeaf));

const allFilesSelected = computed(() => {
    selectionCount.value;
    const files = filesOnCurrentPage.value;
    return files.length > 0 && files.every((file) => isSelected(file));
});

const someFilesSelected = computed(() => {
    selectionCount.value;
    const files = filesOnCurrentPage.value;
    const selectedCount = files.filter((file) => isSelected(file)).length;
    return selectedCount > 0 && selectedCount < files.length;
});

function toggleSelectAll() {
    const files = filesOnCurrentPage.value;
    const allSelected = files.every((file) => isSelected(file));

    files.forEach((file) => {
        const needsToggle = allSelected ? isSelected(file) : !isSelected(file);
        if (needsToggle) {
            selectionModel.value.add(file);
        }
    });
    selectionCount.value = selectionModel.value.count();
}

function entryToSelectionItem(entry: RemoteEntry): SelectionItem {
    return {
        id: entry.uri,
        label: entry.name,
        url: entry.uri,
        isLeaf: entry.class === "File",
        details: "No details available",
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

/**
 * Apply client-side search filter to items
 */
function filterItemsBySearch(items: SelectionItem[]): SelectionItem[] {
    if (!searchQuery.value) {
        return items;
    }
    const query = searchQuery.value.toLowerCase();
    return items.filter((item) => item.label.toLowerCase().includes(query));
}

/**
 * Apply client-side pagination to items
 */
function paginateItems(items: SelectionItem[]): SelectionItem[] {
    const start = (currentPage.value - 1) * perPage.value;
    const end = start + perPage.value;
    return items.slice(start, end);
}

/**
 * Update browser items with client-side filtering and pagination
 */
function updateClientSideView() {
    const filteredItems = filterItemsBySearch(allFetchedItems.value);
    browserItems.value = paginateItems(filteredItems);
    totalMatches.value = filteredItems.length;
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
    const hasServerPagination = supportsServerPagination.value;
    const hasServerSearch = supportsServerSearch.value;

    // Only pass pagination/search params if the file source supports them
    const limit = hasServerPagination ? perPage.value : undefined;
    const offset = hasServerPagination ? (currentPage.value - 1) * perPage.value : undefined;
    const query = hasServerSearch ? searchQuery.value || undefined : undefined;

    await executeIfLatest(
        () => browseRemoteFiles(uri, false, false, limit, offset, query),
        (result) => {
            const allEntries = result.entries.map(entryToSelectionItem);

            if (hasServerPagination) {
                // Server handles pagination and search
                browserItems.value = allEntries;
                totalMatches.value = result.totalMatches;
            } else {
                // Client-side filtering and pagination
                allFetchedItems.value = allEntries;
                updateClientSideView();
            }
        },
        (error) => {
            browserItems.value = [];
            allFetchedItems.value = [];
            totalMatches.value = 0;
            errorMessage.value = errorMessageAsString(error);
        },
    );
}

async function load() {
    // Bump sequence id so any in-flight requests are considered stale
    loadSequenceId.value += 1;
    if (urlTracker.isAtRoot.value) {
        allFetchedItems.value = [];
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

function onRowClick(event: { item: SelectionItem }) {
    onItemClick(event.item);
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
const browserFields: TableField[] = [
    {
        key: "select",
        label: "",
        width: "40px",
        align: "center",
    },
    {
        key: "user",
        label: "",
        sortable: false,
        width: "35px",
        align: "center",
    },
    {
        key: "name",
        label: "Name",
        sortable: false,
        align: "center",
    },
    {
        key: "details",
        label: "Details",
        sortable: false,
        align: "left",
    },
];

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
    selectionModel.value = new Model({ multiple: true });
    selectionCount.value = 0;
    allFetchedItems.value = [];
    clearSearch();
    urlTracker.reset();
    currentPage.value = 1;
    load();
    showBrowser.value = true;
}

function clearSearch() {
    searchQuery.value = "";
}

function updateSearchQuery(newQuery: string) {
    searchQuery.value = newQuery;
}

function startUpload() {
    const uploads = remoteFileItems.value.map((item) => mapToRemoteFileUpload(item, props.targetHistoryId));
    const collectionConfig = buildCollectionConfig(props.targetHistoryId);

    uploadQueue.enqueue(uploads, collectionConfig);

    // Reset state
    remoteFileItems.value = [];
    clearStaging();
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
    if (urlTracker.isAtRoot.value || supportsServerSearch.value) {
        load();
    } else if (allFetchedItems.value.length > 0) {
        updateClientSideView();
    }
});

watch(currentPage, () => {
    if (urlTracker.isAtRoot.value) {
        return;
    }

    if (supportsServerPagination.value) {
        load();
    } else if (allFetchedItems.value.length > 0) {
        updateClientSideView();
    }
});

function onErrorRetry() {
    errorMessage.value = undefined;
    currentPage.value = 1;
    allFetchedItems.value = [];
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
                <div v-else>
                    <span class="font-weight-bold">Browse a File Source below</span> or
                    <GButton color="grey" size="small" @click="createNewFileSource">
                        <FontAwesomeIcon :icon="faPlus" class="mr-1" />
                        Connect New Remote Source
                    </GButton>
                </div>
            </div>

            <!-- Search bar -->
            <div class="search-bar-container mb-2">
                <DataDialogSearch
                    :value="searchQuery"
                    :title="urlTracker.isAtRoot.value ? 'file sources' : 'files and folders'"
                    @input="updateSearchQuery" />
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
                <GTable
                    v-if="!errorMessage && (browserItems.length > 0 || isBusy)"
                    :items="browserItems"
                    :fields="browserFields"
                    :overlay-loading="isBusy"
                    hover
                    striped
                    clickable-rows
                    compact
                    fixed
                    class="browser-table"
                    @row-click="onRowClick">
                    <!-- Select column header (select all) -->
                    <template v-slot:head(select)>
                        <BFormCheckbox
                            v-if="!urlTracker.isAtRoot.value && filesOnCurrentPage.length > 0"
                            :checked="allFilesSelected"
                            :indeterminate="someFilesSelected"
                            @change="toggleSelectAll"
                            @click.stop />
                    </template>

                    <!-- Select column (only for files) -->
                    <template v-slot:cell(select)="{ item }">
                        <BFormCheckbox
                            v-if="item.isLeaf"
                            :checked="isSelected(item)"
                            @change="toggleFileSelection(item)"
                            @click.stop />
                    </template>

                    <!-- Icon column (for highlighting user-created file sources) -->
                    <template v-slot:cell(user)="{ item }">
                        <span
                            v-if="urlTracker.isAtRoot.value && !item.isLeaf && item.url.startsWith(USER_FILE_PREFIX)"
                            v-b-tooltip.hover.noninteractive
                            title="You created this file source">
                            <FontAwesomeIcon :icon="faUser" class="text-primary" fixed-width />
                        </span>
                        <span
                            v-else-if="urlTracker.isAtRoot.value && !item.isLeaf"
                            v-b-tooltip.hover.noninteractive
                            title="This file source was created by an administrator and is globally available">
                            <FontAwesomeIcon :icon="faGlobe" class="text-primary" fixed-width />
                        </span>
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
                        <RemoteEntryMetadata v-if="item.isLeaf && item.entry" :entry="item.entry" />
                        <span v-else-if="urlTracker.isAtRoot && item.details">
                            {{ item.details }}
                        </span>
                    </template>

                    <!-- Loading slot -->
                </GTable>

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
            <div v-if="hasPagination" class="mt-2">
                <BPagination
                    v-model="currentPage"
                    :total-rows="totalMatches"
                    :per-page="perPage"
                    align="center"
                    size="sm" />
            </div>

            <!-- Action buttons -->
            <div class="browser-actions mt-3">
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
                        <button
                            v-b-tooltip.hover.noninteractive
                            class="btn btn-link text-danger remove-btn"
                            title="Remove file from list"
                            @click="removeItem(item.id)">
                            <FontAwesomeIcon :icon="faTimes" />
                        </button>
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

    :deep(.browser-table thead) {
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
