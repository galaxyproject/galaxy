<script setup lang="ts">
import { faDatabase, faFile, faFolder, faLock, faPlus, faShieldAlt, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BFormCheckbox, BPagination, BTable } from "bootstrap-vue";
import { computed, nextTick, onMounted, ref, watch } from "vue";

import type {
    AnyLibraryFolderItem,
    GetFolderContentsOptions,
    LibraryFolderContentsIndexResult,
    LibrarySummary,
    SortBy,
} from "@/api/libraries";
import { getFolderContents, getLibraries, isLibraryFile } from "@/api/libraries";
import type { BreadcrumbItem } from "@/components/Common";
import { Model } from "@/components/FilesDialog/model";
import type { SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import { useCollectionCreation } from "@/composables/upload/collectionCreation";
import { useUploadReadyState } from "@/composables/upload/uploadReadyState";
import { useUploadQueue } from "@/composables/uploadQueue";
import { useUrlTracker } from "@/composables/urlTracker";
import { useUploadStagingStore } from "@/stores/uploadStagingStore";
import { errorMessageAsString } from "@/utils/simple-error";
import { mapToLibraryDatasetUpload } from "@/utils/upload/itemMappers";
import { bytesToString } from "@/utils/utils";

import type { UploadMethodComponent, UploadMethodConfig } from "../types";
import type { LibraryDatasetItem } from "../types/uploadItem";

import CollectionCreationConfig from "../CollectionCreationConfig.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbNavigation from "@/components/Common/BreadcrumbNavigation.vue";
import DataDialogSearch from "@/components/SelectionDialog/DataDialogSearch.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    method: UploadMethodConfig;
    targetHistoryId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "ready", ready: boolean): void;
}>();

const uploadQueue = useUploadQueue();

const tableContainerRef = ref<HTMLElement | null>(null);
const collectionConfigComponent = ref<InstanceType<typeof CollectionCreationConfig> | null>(null);
const stagingStore = useUploadStagingStore();

const { collectionState, handleCollectionStateChange, buildCollectionConfig, resetCollection } =
    useCollectionCreation(collectionConfigComponent);

let nextId = 1;

/**
 * Converts a library folder item (folder or dataset) to a SelectionItem for navigation tracking
 */
function folderItemToSelectionItem(item: AnyLibraryFolderItem, libraryId: string): SelectionItem {
    const isFolder = item.type === "folder";
    const details = isFolder ? item.description : null;

    return {
        id: item.id,
        label: item.name,
        url: isFolder ? `/api/folders/${item.id}` : `/api/libraries/datasets/${item.id}`,
        isLeaf: !isFolder,
        details: details || "No description available",
        entry: {
            ...item,
            libraryId,
        },
    };
}

/**
 * Creates a LibraryDatasetItem from a library dataset metadata
 */
function createLibraryDatasetItem(item: AnyLibraryFolderItem, libraryId: string, folderId: string): LibraryDatasetItem {
    if (!isLibraryFile(item)) {
        throw new Error("Item is not a library dataset");
    }

    return {
        id: nextId++,
        libraryId,
        folderId,
        lddaId: item.ldda_id,
        url: `/api/libraries/datasets/${item.id}`,
        name: item.name,
        extension: item.file_ext,
        size: item.raw_size,
        created: item.create_time,
        updated: item.update_time,
        dateUploaded: item.date_uploaded,
        isUnrestricted: item.is_unrestricted,
        isPrivate: item.is_private,
        tags: item.tags || [],
    };
}

const showBrowser = ref(true);
const libraryDatasetItems = ref<LibraryDatasetItem[]>([]);

onMounted(() => {
    const staged = stagingStore.getItems<LibraryDatasetItem>(props.method.id);
    if (staged.length) {
        libraryDatasetItems.value = staged;
        nextId = Math.max(...staged.map((i) => i.id)) + 1;
        showBrowser.value = false;
    }
});

watch(
    libraryDatasetItems,
    (items) => {
        stagingStore.setItems(props.method.id, items);
    },
    { deep: true },
);

const selectionModel = ref<Model>(new Model({ multiple: true }));
const selectionCount = ref(0);

// Navigation state
type LibraryNavigationItem = SelectionItem & { libraryId: string; folderId?: string };
const urlTracker = useUrlTracker<LibraryNavigationItem>();
const currentLibrary = ref<LibrarySummary | null>(null);
const currentFolderId = ref<string | null>(null);

// Browser data
const libraries = ref<LibrarySummary[]>([]);
const browserItems = ref<SelectionItem[]>([]);

// UI state
const searchQuery = ref("");
const isBusy = ref(false);
const errorMessage = ref<string>();
const currentPage = ref(1);
const perPage = ref(25);
const totalMatches = ref(0);
const sortBy = ref<SortBy>("name"); // API field name
const tableSortBy = ref("name"); // Table column key
const sortDesc = ref(false);

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

const hasPagination = computed(() => {
    if (!currentLibrary.value || isBusy.value) {
        return false;
    }
    return totalMatches.value > perPage.value;
});

const hasItems = computed(() => libraryDatasetItems.value.length > 0);
const hasSelection = computed(() => selectionCount.value > 0);

const searchTitle = computed(() => {
    if (!currentLibrary.value) {
        return "libraries";
    }
    return "datasets and folders";
});

const filteredLibraries = computed(() => {
    if (!searchQuery.value) {
        return libraries.value;
    }
    const query = searchQuery.value.toLowerCase();
    return libraries.value.filter(
        (lib) =>
            lib.name.toLowerCase().includes(query) ||
            (lib.description && lib.description.toLowerCase().includes(query)),
    );
});

const breadcrumbs = computed(() => {
    const crumbs: BreadcrumbItem[] = [{ title: "Libraries", index: -1 }];
    if (currentLibrary.value) {
        crumbs.push({ title: currentLibrary.value.name, index: 0 });
    }
    urlTracker.navigationHistory.value.forEach((item, index) => {
        if (index > 0) {
            // Skip the root folder (index 0 is library itself)
            crumbs.push({ title: item.label, index });
        }
    });
    return crumbs;
});

const { isReadyToUpload } = useUploadReadyState(hasItems, collectionState);

watch(isReadyToUpload, (ready) => emit("ready", ready), { immediate: true });

const datasetsOnCurrentPage = computed(() => browserItems.value.filter((item) => item.isLeaf));

const allDatasetsSelected = computed(() => {
    selectionCount.value;
    const datasets = datasetsOnCurrentPage.value;
    return datasets.length > 0 && datasets.every((dataset) => isSelected(dataset));
});

const someDatasetsSelected = computed(() => {
    selectionCount.value;
    const datasets = datasetsOnCurrentPage.value;
    const selectedCount = datasets.filter((dataset) => isSelected(dataset)).length;
    return selectedCount > 0 && selectedCount < datasets.length;
});

function toggleSelectAll() {
    const datasets = datasetsOnCurrentPage.value;
    const allSelected = datasets.every((dataset) => isSelected(dataset));

    datasets.forEach((dataset) => {
        const needsToggle = allSelected ? isSelected(dataset) : !isSelected(dataset);
        if (needsToggle) {
            selectionModel.value.add(dataset);
        }
    });
    selectionCount.value = selectionModel.value.count();
}

function isSelected(item: SelectionItem): boolean {
    return selectionModel.value.exists(item.id);
}

function toggleFileSelection(item: SelectionItem) {
    if (item.isLeaf) {
        selectionModel.value.add(item);
        selectionCount.value = selectionModel.value.count();
    }
}

function onItemClick(item: SelectionItem) {
    // Don't allow navigation or selection while loading or if there's an error
    if (isBusy.value || errorMessage.value) {
        return;
    }

    if (!item.isLeaf) {
        // Navigate into directory
        navigateToFolder(item);
    } else {
        // Toggle file selection
        selectionModel.value.add(item);
        selectionCount.value = selectionModel.value.count();
    }
}

/**
 * Load all accessible libraries
 */
async function loadLibraries() {
    loadSequenceId.value++;
    await executeIfLatest(
        () => getLibraries(),
        (data) => {
            libraries.value = data;
            currentLibrary.value = null;
            currentFolderId.value = null;
            browserItems.value = [];
            showBrowser.value = true;
            // Reset sorting when viewing libraries
            sortBy.value = "name";
            tableSortBy.value = "name";
            sortDesc.value = false;
        },
    );
}

/**
 * Load folder contents
 */
async function loadFolderContents(folderId: string) {
    loadSequenceId.value++;

    const options: GetFolderContentsOptions = {
        searchText: searchQuery.value || undefined,
        sortBy: sortBy.value,
        sortDesc: sortDesc.value,
        limit: perPage.value,
        offset: (currentPage.value - 1) * perPage.value,
    };

    await executeIfLatest(
        () => getFolderContents(folderId, options),
        (result: LibraryFolderContentsIndexResult) => {
            const contents = result.folder_contents || [];

            // Convert to browser items
            browserItems.value = contents.map((item) => folderItemToSelectionItem(item, currentLibrary.value!.id));

            // Use total_rows from metadata for pagination
            totalMatches.value = result.metadata?.total_rows || contents.length;
        },
        (error) => {
            browserItems.value = [];
            totalMatches.value = 0;
            errorMessage.value = errorMessageAsString(error);
        },
    );
}

/**
 * Navigate to a library (show its root folder)
 */
async function selectLibrary(library: LibrarySummary) {
    currentLibrary.value = library;
    currentFolderId.value = library.root_folder_id;

    // Reset navigation history and add library root
    urlTracker.reset();
    const rootItem: LibraryNavigationItem = {
        id: library.root_folder_id,
        label: library.name,
        url: `/api/folders/${library.root_folder_id}`,
        isLeaf: false,
        details: library.description || "",
        entry: {},
        libraryId: library.id,
        folderId: library.root_folder_id,
    };
    urlTracker.forward(rootItem);

    // Reset pagination, search, and sorting
    currentPage.value = 1;
    searchQuery.value = "";
    sortBy.value = "name";
    tableSortBy.value = "name";
    sortDesc.value = false;

    await loadFolderContents(library.root_folder_id);
}

/**
 * Navigate into a folder (when clicking on a folder in the browser)
 */
function navigateToFolder(item: SelectionItem) {
    if (item.isLeaf) {
        return; // Can't navigate into datasets
    }

    const navItem = item as LibraryNavigationItem;
    navItem.libraryId = currentLibrary.value!.id;
    navItem.folderId = item.id;

    urlTracker.forward(navItem);
    currentFolderId.value = item.id;
    currentPage.value = 1;
    loadFolderContents(item.id);
}

/**
 * Navigate via breadcrumb navigation
 */
async function navigateToBreadcrumb(index: number) {
    if (index === -1) {
        // Back to library list
        urlTracker.reset();
        await loadLibraries();
        return;
    }

    if (index === 0) {
        // Back to library root
        await selectLibrary(currentLibrary.value!);
        return;
    }

    // Navigate to specific folder in history
    const historyItem = urlTracker.navigationHistory.value[index];
    const navItem = historyItem as LibraryNavigationItem;

    // Reset navigation to this index
    const targetDepth = index + 1;
    const currentDepth = urlTracker.navigationHistory.value.length;
    const stepsBack = currentDepth - targetDepth;

    for (let i = 0; i < stepsBack; i++) {
        urlTracker.backward();
    }

    currentFolderId.value = navItem.folderId!;
    currentPage.value = 1;
    await loadFolderContents(navItem.folderId!);
}

function addSelectedDatasets() {
    const selectedItems = selectionModel.value.finalize() as SelectionItem[];

    // Filter out any items that already exist in libraryDatasetItems
    const existingUrls = new Set(libraryDatasetItems.value.map((item) => item.url));
    const newItems = selectedItems.filter((item) => !existingUrls.has(item.url));
    const libraryId = currentLibrary.value!.id;

    // Add new items
    for (const item of newItems) {
        if (isLibraryFile(item.entry)) {
            libraryDatasetItems.value.push(createLibraryDatasetItem(item.entry, libraryId, currentFolderId.value!));
        }
    }

    // Clear selection and switch to table view
    selectionModel.value = new Model({ multiple: true });
    selectionCount.value = 0;
    showBrowser.value = false;
    scrollToBottom();
}

function showDatasetList() {
    showBrowser.value = false;
}

function showFolderBrowser() {
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
    libraryDatasetItems.value = libraryDatasetItems.value.filter((item) => item.id !== id);
}

function clearAll() {
    libraryDatasetItems.value = [];
    resetCollection();
    selectionModel.value = new Model({ multiple: true });
    selectionCount.value = 0;
    searchQuery.value = "";
    urlTracker.reset();
    currentPage.value = 1;
    loadLibraries();
    showBrowser.value = true;
}

function clearSearch() {
    searchQuery.value = "";
}

function updateSearchQuery(newQuery: string) {
    searchQuery.value = newQuery;
}

function startUpload() {
    const uploads = libraryDatasetItems.value.map((item) => mapToLibraryDatasetUpload(item, props.targetHistoryId));
    const collectionConfig = buildCollectionConfig(props.targetHistoryId);

    uploadQueue.enqueue(uploads, collectionConfig);

    // Reset state
    libraryDatasetItems.value = [];
    stagingStore.clearItems(props.method.id);
    showBrowser.value = true;
    resetCollection();
    selectionModel.value = new Model({ multiple: true });
    selectionCount.value = 0;
    clearSearch();
    urlTracker.reset();
}

const libraryFields = [
    {
        key: "name",
        label: "Name",
        sortable: true,
        thStyle: { width: "auto" },
        tdClass: "align-middle",
    },
    {
        key: "synopsis",
        label: "Synopsis",
        sortable: false,
    },
    {
        key: "description",
        label: "Description",
        sortable: false,
        thStyle: { width: "auto" },
        tdClass: "align-middle",
    },
];

// Browser table fields
const browserFields = [
    {
        key: "select",
        label: "",
        thStyle: { width: "25px" },
        tdClass: "align-middle",
    },
    {
        key: "permission",
        label: "",
        sortable: false,
        thStyle: { width: "20px" },
        tdClass: "align-middle text-center",
    },
    {
        key: "type",
        label: "",
        sortable: false,
        thStyle: { width: "20px" },
        tdClass: "align-middle text-center",
    },
    {
        key: "name",
        label: "Name",
        sortable: true,
        thStyle: { minWidth: "200px" },
        tdClass: "align-middle",
    },
    {
        key: "size",
        label: "Size",
        sortable: true,
        thStyle: { width: "100px" },
        tdClass: "align-middle text-right",
    },
    {
        key: "updated",
        label: "Updated",
        sortable: true,
        thStyle: { width: "auto", minWidth: "150px" },
        tdClass: "align-middle text-muted",
    },
];

// Dataset list table fields
const tableFields = [
    {
        key: "name",
        label: "Name",
        sortable: true,
        thStyle: { width: "auto" },
        tdClass: "file-name-cell align-middle",
    },
    {
        key: "extension",
        label: "Type",
        sortable: false,
        thStyle: { minWidth: "120px", width: "120px" },
        tdClass: "align-middle text-muted",
    },
    {
        key: "size",
        label: "Size",
        sortable: true,
        thStyle: { minWidth: "100px", width: "100px" },
        tdClass: "align-middle text-right",
    },
    { key: "actions", label: "", sortable: false, tdClass: "text-right align-middle", thStyle: { width: "50px" } },
];

/**
 * Handle search query change - reload folder contents with new search
 */
watch(searchQuery, async () => {
    if (currentFolderId.value) {
        currentPage.value = 1;
        await loadFolderContents(currentFolderId.value);
    }
    // For library list, search is handled by filteredLibraries computed property
});

/**
 * Handle pagination change
 */
watch(currentPage, async () => {
    if (currentFolderId.value) {
        await loadFolderContents(currentFolderId.value);
    }
});

/**
 * Map table column keys to API sort field names
 */
function mapSortKeyToApiField(key: string): SortBy {
    const mapping: Record<string, SortBy> = {
        name: "name",
        description: "description",
        type: "type",
        size: "size",
        updated: "update_time",
    };
    return mapping[key] || "name";
}

function onSortChanged(ctx: { sortBy: string; sortDesc: boolean }) {
    const apiSortField = mapSortKeyToApiField(ctx.sortBy);
    tableSortBy.value = ctx.sortBy; // Store table column key
    sortBy.value = apiSortField; // Store API field name
    sortDesc.value = ctx.sortDesc;
    currentPage.value = 1; // Reset to first page when sorting changes

    if (currentFolderId.value) {
        loadFolderContents(currentFolderId.value);
    }
}

function onErrorRetry() {
    errorMessage.value = undefined;
    currentPage.value = 1;
    clearSearch();

    if (currentFolderId.value) {
        loadFolderContents(currentFolderId.value);
    } else {
        loadLibraries();
    }
}

function getPermissionIcon(entry: AnyLibraryFolderItem) {
    if (isLibraryFile(entry)) {
        if (entry.is_private) {
            return faLock;
        }
        if (!entry.is_unrestricted) {
            return faShieldAlt;
        }
    }
    return undefined;
}

function getPermissionTitle(entry: AnyLibraryFolderItem) {
    if (isLibraryFile(entry)) {
        if (entry.is_private) {
            return "This dataset is private to you.";
        }
        if (!entry.is_unrestricted) {
            return "This dataset has restricted access. Only specified users can access it.";
        }
    }
    return undefined;
}

// Initialize: load libraries (only if not showing staged items)
onMounted(async () => {
    if (showBrowser.value) {
        await loadLibraries();
    }
});

defineExpose<UploadMethodComponent>({ startUpload });
</script>

<template>
    <div class="data-library-upload">
        <!-- Library Browser Phase -->
        <div v-if="showBrowser" class="library-browser">
            <!-- Navigation breadcrumb -->
            <div class="browser-header mb-2">
                <BreadcrumbNavigation
                    v-if="!urlTracker.isAtRoot.value"
                    :items="breadcrumbs"
                    @navigate="navigateToBreadcrumb" />
                <span v-else class="font-weight-bold"> Browse a Data Library below </span>
            </div>

            <!-- Search bar -->
            <div class="search-bar-container mb-2">
                <DataDialogSearch :value="searchQuery" :title="searchTitle" @input="updateSearchQuery" />
            </div>

            <!-- Error message -->
            <BAlert v-if="errorMessage" variant="danger" show dismissible @dismissed="errorMessage = undefined">
                <div class="d-flex justify-content-between align-items-center">
                    <span>{{ errorMessage }}</span>
                    <GButton color="red" class="ml-2" @click="onErrorRetry"> Retry </GButton>
                </div>
            </BAlert>

            <!-- Library List View -->
            <div v-if="!currentLibrary" class="browser-table-container">
                <BTable
                    v-if="!errorMessage && filteredLibraries.length > 0"
                    :items="filteredLibraries"
                    :fields="libraryFields"
                    :busy="isBusy"
                    striped
                    hover
                    small
                    fixed
                    thead-class="browser-table-header"
                    @row-clicked="selectLibrary">
                    <template v-slot:table-busy>
                        <div class="text-center my-2">
                            <b-spinner small class="align-middle"></b-spinner>
                            <strong class="ml-2">Loading...</strong>
                        </div>
                    </template>

                    <template v-slot:cell(name)="{ item }">
                        <FontAwesomeIcon :icon="faDatabase" class="mr-2 text-primary" />
                        <strong>{{ item.name }}</strong>
                    </template>
                </BTable>

                <!-- Empty state message when no libraries are available -->
                <div v-else-if="!errorMessage && !isBusy" class="text-center text-muted my-5">
                    <p v-if="searchQuery" class="lead">No libraries match your search "{{ searchQuery }}"</p>
                    <p v-else class="lead">No libraries available.</p>
                </div>
            </div>

            <!-- Folder Browser View -->
            <div v-else class="browser-table-container">
                <BTable
                    v-if="!errorMessage && browserItems.length > 0"
                    :items="browserItems"
                    :fields="browserFields"
                    :busy="isBusy"
                    :sort-by.sync="tableSortBy"
                    :sort-desc.sync="sortDesc"
                    striped
                    small
                    hover
                    fixed
                    thead-class="browser-table-header"
                    @sort-changed="onSortChanged"
                    @row-clicked="onItemClick">
                    <template v-slot:head(select)>
                        <BFormCheckbox
                            v-if="datasetsOnCurrentPage.length > 0"
                            :checked="allDatasetsSelected"
                            :indeterminate="someDatasetsSelected"
                            @change="toggleSelectAll" />
                    </template>

                    <template v-slot:cell(select)="{ item }">
                        <BFormCheckbox
                            v-if="item.isLeaf"
                            :checked="isSelected(item)"
                            @change="toggleFileSelection(item)"
                            @click.stop />
                    </template>

                    <template v-slot:cell(permission)="{ item }">
                        <span
                            v-if="getPermissionIcon(item.entry)"
                            v-b-tooltip.hover
                            class="mr-2 text-muted"
                            :title="getPermissionTitle(item.entry)">
                            <FontAwesomeIcon :icon="getPermissionIcon(item.entry)" />
                        </span>
                    </template>

                    <template v-slot:cell(type)="{ item }">
                        <FontAwesomeIcon
                            :icon="item.isLeaf ? faFile : faFolder"
                            :class="item.isLeaf ? 'text-muted' : 'text-warning'" />
                    </template>

                    <template v-slot:cell(name)="{ item }">
                        <div class="d-flex align-items-center">
                            <span>{{ item.label }}</span>
                        </div>
                    </template>

                    <template v-slot:cell(size)="{ item }">
                        <span v-if="item.isLeaf && item.entry && item.entry.file_size">
                            {{ item.entry.file_size }}
                        </span>
                        <span v-else class="text-muted">—</span>
                    </template>

                    <template v-slot:cell(updated)="{ item }">
                        <UtcDate
                            v-if="item.entry && item.entry.update_time"
                            :date="item.entry.update_time"
                            mode="pretty" />
                        <span v-else class="text-muted">—</span>
                    </template>

                    <template v-slot:table-busy>
                        <div class="text-center my-2">
                            <b-spinner small class="align-middle"></b-spinner>
                            <strong class="ml-2">Loading...</strong>
                        </div>
                    </template>
                </BTable>

                <!-- Empty state message when no items are available -->
                <div v-else-if="!errorMessage && !isBusy" class="text-center text-muted my-5">
                    <p v-if="searchQuery" class="lead">No datasets or folders match your search "{{ searchQuery }}"</p>
                    <p v-else class="lead">This folder is empty or you do not have access to its contents.</p>
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
            <div v-if="currentLibrary" class="browser-actions mt-3">
                <GButton v-if="hasItems && !hasSelection" color="grey" outline @click="showDatasetList">
                    View Selected Datasets ({{ libraryDatasetItems.length }})
                </GButton>
                <GButton color="blue" :disabled="!hasSelection" class="ml-auto" @click="addSelectedDatasets">
                    <FontAwesomeIcon :icon="faPlus" class="mr-1" />
                    Add Selected Datasets ({{ selectionCount }})
                </GButton>
            </div>
        </div>

        <!-- Dataset List Phase -->
        <div v-else class="dataset-list">
            <div class="file-list-header mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <span class="font-weight-bold">{{ libraryDatasetItems.length }} dataset(s) selected</span>
                </div>
            </div>

            <div ref="tableContainerRef" class="file-table-container">
                <BTable
                    :items="libraryDatasetItems"
                    :fields="tableFields"
                    small
                    striped
                    thead-class="file-table-header">
                    <template v-slot:cell(name)="{ item }">
                        <span class="font-weight-medium">{{ item.name }}</span>
                    </template>

                    <template v-slot:cell(extension)="{ item }">
                        {{ item.extension }}
                    </template>

                    <template v-slot:cell(size)="{ item }">
                        {{ bytesToString(item.size) }}
                    </template>

                    <template v-slot:cell(actions)="{ item }">
                        <button
                            v-b-tooltip.hover.noninteractive
                            class="btn btn-link text-danger remove-btn"
                            title="Remove dataset from list"
                            @click="removeItem(item.id)">
                            <FontAwesomeIcon :icon="faTimes" />
                        </button>
                    </template>
                </BTable>
            </div>

            <!-- Collection Creation Section -->
            <CollectionCreationConfig
                ref="collectionConfigComponent"
                :files="libraryDatasetItems"
                @update:state="handleCollectionStateChange" />

            <div class="file-list-actions mt-2">
                <GButton
                    color="grey"
                    tooltip
                    tooltip-placement="top"
                    title="Add more datasets to the upload list"
                    @click="showFolderBrowser">
                    <FontAwesomeIcon :icon="faPlus" class="mr-1" />
                    Add More Datasets
                </GButton>
                <GButton
                    outline
                    color="grey"
                    tooltip
                    tooltip-placement="top"
                    title="Remove all datasets from the upload list"
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

.data-library-upload {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.library-browser {
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

.dataset-list {
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
}

.file-list-actions {
    @include upload-list-actions;
}

.cursor-pointer {
    cursor: pointer;
}
</style>
