<script setup lang="ts">
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import Vue, { computed, nextTick, onMounted, ref, watch } from "vue";

import {
    browseRemoteFiles,
    fetchFileSources,
    type FileSourceBrowsingMode,
    type FilterFileSourcesOptions,
    type RemoteEntry,
} from "@/api/remoteFiles";
import { fileSourcePluginToItem, isSamePath, isSubPath } from "@/components/FilesDialog/utilities";
import {
    type ItemsProvider,
    type ItemsProviderContext,
    SELECTION_STATES,
    type SelectionItem,
    type SelectionState,
} from "@/components/SelectionDialog/selectionTypes";
import { useConfig } from "@/composables/config";
import { useFileSources } from "@/composables/fileSources";
import { useUrlTracker } from "@/composables/urlTracker";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";
import { errorMessageAsString } from "@/utils/simple-error";
import { USER_FILE_PREFIX } from "@/utils/url";

import { Model } from "./model";

import GButton from "../BaseComponents/GButton.vue";
import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

const filesSources = useFileSources();

interface FilesDialogProps {
    /** Callback function to be called passing the results when selection is complete */
    callback?: (files: SelectionItem | SelectionItem[]) => void;
    /** Options to filter the file sources */
    filterOptions?: FilterFileSourcesOptions;
    /** Decide wether to keep the underlying modal static or dynamic */
    modalStatic?: boolean;
    /** Browsing mode to define the selection behavior */
    mode?: FileSourceBrowsingMode;
    /** Whether to allow multiple selections */
    multiple?: boolean;
    /** Whether to show only writable sources */
    requireWritable?: boolean;
    /** Optional selected item to start browsing from */
    selectedItem?: SelectionItem;
    /** Whether the dialog is visible at the start */
    isOpen?: boolean;
    /** Function to push a new route, used for navigation */
    routePush?: (route: string) => void;
}

const props = withDefaults(defineProps<FilesDialogProps>(), {
    callback: () => {},
    filterOptions: undefined,
    modalStatic: false,
    mode: "file",
    multiple: false,
    requireWritable: false,
    selectedItem: undefined,
    isOpen: true,
    routePush: () => {},
});

const { config, isConfigLoaded } = useConfig();

const selectionModel = ref<Model>(new Model({ multiple: props.multiple }));

const query = ref<string>();
const selectionDialog = ref();
const allSelected = ref(false);
const selectedDirectories = ref<SelectionItem[]>([]);
const errorMessage = ref<string>();
const filter = ref();
const items = ref<SelectionItem[]>([]);
const itemsProvider = ref<ItemsProvider>();
const modalShow = ref(props.isOpen);
const optionsShow = ref(false);
const undoShow = ref(false);
const hasValue = ref(false);
const showTime = ref(true);
const showDetails = ref(true);
const isBusy = ref(false);
/** Recursive folder listings still loading; the files they return are not selected yet */
const pendingListings = ref(0);
/** Latest recursive listing of each folder still loading; earlier or abandoned listings are ignored */
const folderListings = new Map<string, symbol>();
const showFTPHelper = ref(false);
/** Root URIs of RDM sources, only fetched in directory mode to prevent selecting a repository root */
const rdmUriRoots = ref<string[]>([]);
const selectAllIcon = ref<SelectionState>(SELECTION_STATES.UNSELECTED);
const urlTracker = useUrlTracker<SelectionItem & { parentPage?: number }>({ root: undefined });
const totalItems = ref(0);

const fields = computed(() => {
    const fields = [];
    fields.push({ key: "label" });
    if (showDetails.value) {
        fields.push({ key: "details" });
    }
    if (showTime.value) {
        fields.push({ key: "time" });
    }
    return fields;
});

const fileMode = computed(() => props.mode == "file");

/** The rows are one page of a paginated folder, or its filter matches, rather than all of its contents */
const isPaginated = computed(
    () => Boolean(itemsProvider.value) && (totalItems.value > items.value.length || Boolean(query.value)),
);

/** RDM repositories (e.g. Dataverse, Invenio) only hold files inside their records, not at their root */
const isAtRdmRepositoryRoot = computed(() => {
    const url = urlTracker.current.value?.url;
    if (!url) {
        return false;
    }
    return rdmUriRoots.value.some((uriRoot) => isSamePath(url, uriRoot));
});

const okButtonDisabled = computed(
    () =>
        (fileMode.value && !hasValue.value) ||
        isBusy.value ||
        pendingListings.value > 0 ||
        (!fileMode.value && (urlTracker.isAtRoot.value || isAtRdmRepositoryRoot.value)),
);

const canCreateNewFileSource = computed(() => {
    return urlTracker.isAtRoot.value && fileSourceTemplatesStore.hasTemplates;
});

const fileSourceTemplatesStore = useFileSourceTemplatesStore();
fileSourceTemplatesStore.ensureTemplates();

/** Collects selected datasets in value array **/
function clicked(record: SelectionItem) {
    // ignore the click during directory mode
    if (!fileMode.value) {
        return;
    }
    if (record.isLeaf) {
        // record is file
        selectSingleRecord(record);
    } else {
        // you cannot select entire root directory
        urlTracker.isAtRoot.value ? open(record) : selectDirectoryRecursive(record);
    }
    formatRows();
}

function selectSingleRecord(record: SelectionItem, selectOnly = false) {
    const selected = selectionModel.value.exists(record.id);
    if (selected) {
        unselectPath(record.url, true);
    }
    if (selectOnly) {
        if (!selected) {
            selectionModel.value.add(record);
        }
    } else {
        selectionModel.value.add(record);
    }
    hasValue.value = selectionModel.value.count() > 0;
    if (props.multiple) {
        formatRows();
    } else {
        finalize();
    }
}

function unselectPath(path: string, unselectOnlyAboveDirectories = false, unselectId?: string) {
    // unselect directories
    selectedDirectories.value = selectedDirectories.value.filter((directory) => {
        if (unselectId === directory.id) {
            return false;
        }

        let matched;
        if (unselectOnlyAboveDirectories) {
            matched = isSubPath(directory.url, path);
        } else {
            // unselect all folders under or above the current path
            matched = isSubPath(directory.url, path) || isSubPath(path, directory.url);
        }
        // filter out those that matched
        return !matched;
    });

    // unselect files
    if (!unselectOnlyAboveDirectories) {
        // unselect all files under this path
        selectionModel.value.unselectUnderPath(path);
    }
}

function selectDirectoryRecursive(record: SelectionItem) {
    // if directory is `selected` or `mixed` unselect everything
    if (isDirectorySelected(record.id) || selectionModel.value.pathExists(record.url)) {
        unselectPath(record.url, false, record.id);
        endFolderListing(record.id);
    } else {
        selectedDirectories.value.push(record);
        // look for subdirectories
        const recursive = true;
        const listing = Symbol(record.id);
        endFolderListing(record.id);
        folderListings.set(record.id, listing);
        pendingListings.value++;
        browseRemoteFiles(record.url, recursive)
            .then((incoming) => {
                if (folderListings.get(record.id) !== listing || !isDirectorySelected(record.id)) {
                    return;
                }
                incoming.entries.forEach((item) => {
                    // construct record
                    const subRecord = entryToRecord(item);
                    if (subRecord.isLeaf) {
                        // select file under this path
                        selectSingleRecord(subRecord, true);
                    } else {
                        // select subdirectory
                        selectedDirectories.value.push(subRecord);
                    }
                });
            })
            .finally(() => {
                if (folderListings.get(record.id) === listing) {
                    endFolderListing(record.id);
                }
            });
    }
}

/** Stops waiting for the folder's listing, so its files are not selected when it returns */
function endFolderListing(folderId: string) {
    if (folderListings.delete(folderId)) {
        pendingListings.value--;
    }
}

/** Add highlighting for record variations, i.e. datasets vs. libraries/collections **/
function formatRows() {
    const getIcon = (isSelected: boolean, path: string) => {
        if (isSelected) {
            return SELECTION_STATES.SELECTED;
        } else {
            return selectionModel.value.pathExists(path) ? SELECTION_STATES.MIXED : SELECTION_STATES.UNSELECTED;
        }
    };

    hasValue.value = selectionModel.value.count() > 0 || selectedDirectories.value.length > 0;
    for (const item of items.value) {
        let _rowVariant = "active";
        if (item.isLeaf || !fileMode.value) {
            _rowVariant = selectionModel.value.exists(item.id) ? "success" : "default";
        }
        // if directory
        else if (!item.isLeaf) {
            _rowVariant = getIcon(isDirectorySelected(item.id), item.url);
        }
        Vue.set(item, "_rowVariant", _rowVariant);
    }
    allSelected.value = checkIfAllSelected();
    if (urlTracker.current.value?.url) {
        selectAllIcon.value = getIcon(allSelected.value, urlTracker.current.value.url);
    }
}

function isDirectorySelected(directoryId: string): boolean {
    return selectedDirectories.value.some(({ id }) => id === directoryId);
}

/** whether the row, or anything under it, is selected **/
function isRowSelected(item: SelectionItem): boolean {
    return (
        selectionModel.value.exists(item.id) || selectionModel.value.pathExists(item.id) || isDirectorySelected(item.id)
    );
}

/** check if all objects in this folders are selected **/
function checkIfAllSelected(): boolean {
    const isAllSelected =
        Boolean(items.value.length) &&
        items.value.every(({ id }) => selectionModel.value.exists(id) || isDirectorySelected(id));

    if (
        isAllSelected &&
        !isPaginated.value &&
        urlTracker.current.value &&
        !isDirectorySelected(urlTracker.current.value.id)
    ) {
        // if all selected, select current folder
        selectedDirectories.value.push(urlTracker.current.value);
    }

    return isAllSelected;
}

function open(record: SelectionItem) {
    urlTracker.forward({ ...record, parentPage: selectionDialog.value.currentPage });
    selectionDialog.value?.resetPagination(1);
    load();
}

/** Fetched alongside the root list, so sources created since the dialog was last opened are included */
async function loadRdmUriRoots() {
    if (props.mode !== "directory") {
        return;
    }
    try {
        const rdmFileSources = await fetchFileSources({ include: ["rdm"] });
        rdmUriRoots.value = rdmFileSources.map((fs) => fs.uri_root);
    } catch (error) {
        console.error("Failed to load RDM file sources", error);
    }
}

/** Performs server request to retrieve data records **/
function load() {
    showFTPHelper.value = urlTracker.current.value?.url === "gxftp://";
    filter.value = undefined;
    selectionDialog.value?.resetFilter();
    optionsShow.value = false;
    undoShow.value = !urlTracker.isAtRoot.value;
    if (urlTracker.isAtRoot.value || errorMessage.value) {
        itemsProvider.value = undefined;
        errorMessage.value = undefined;
        isBusy.value = true;
        loadRdmUriRoots();
        fetchFileSources(props.filterOptions)
            .then((results) => {
                const convertedItems = results
                    .filter((item) => !props.requireWritable || item.writable)
                    .map(fileSourcePluginToItem);

                const sortedItems = convertedItems.sort(sortPrivateFileSourcesFirst);
                items.value = sortedItems;
                formatRows();
                showTime.value = false;
                showDetails.value = true;
                totalItems.value = convertedItems.length;
                isBusy.value = false;
                optionsShow.value = true;
            })
            .catch((error) => {
                errorMessage.value = errorMessageAsString(error);
                isBusy.value = false;
            });
    } else {
        if (!urlTracker.current.value) {
            return;
        }
        if (props.mode === "source") {
            // In source mode, only show sources, not contents
            items.value = [];
            optionsShow.value = true;
            showTime.value = false;
            showDetails.value = false;
            return;
        }

        if (shouldUseItemsProvider()) {
            itemsProvider.value = (ctx) => provideItems(ctx, urlTracker.current.value?.url);
            optionsShow.value = true;
            showTime.value = true;
            showDetails.value = false;
            return;
        }

        isBusy.value = true;
        browseRemoteFiles(urlTracker.current.value?.url, false, props.requireWritable)
            .then((result) => {
                items.value = filterByMode(result.entries).map(entryToRecord);
                totalItems.value = result.totalMatches;
                formatRows();
                showTime.value = true;
                showDetails.value = false;
                isBusy.value = false;
                optionsShow.value = true;
            })
            .catch((error) => {
                errorMessage.value = errorMessageAsString(error);
                isBusy.value = false;
            });
    }
}

function isPrivateFileSource(item: SelectionItem): boolean {
    return item.url.startsWith(USER_FILE_PREFIX);
}

function sortPrivateFileSourcesFirst(a: SelectionItem, b: SelectionItem): number {
    if (isPrivateFileSource(a) && !isPrivateFileSource(b)) {
        return -1;
    }
    if (!isPrivateFileSource(a) && isPrivateFileSource(b)) {
        return 1;
    }
    return 0;
}

/**
 * Check if the current file source supports server-side pagination.
 * If it does, we will use the items provider to fetch items.
 */
function shouldUseItemsProvider(): boolean {
    if (!urlTracker.current.value) {
        return false;
    }
    const fileSource = filesSources.getFileSourceByUri(urlTracker.current.value.url);
    const supportsPagination = fileSource?.supports?.pagination;
    return Boolean(supportsPagination);
}

/**
 *  Fetches items from the server using server-side pagination and filtering.
 **/
async function provideItems(ctx: ItemsProviderContext, url?: string): Promise<SelectionItem[]> {
    isBusy.value = true;
    try {
        if (!url) {
            return [];
        }
        const limit = ctx.perPage;
        const offset = (ctx.currentPage ? ctx.currentPage - 1 : 0) * ctx.perPage;
        query.value = ctx.filter;
        const response = await browseRemoteFiles(url, false, props.requireWritable, limit, offset, query.value);
        const result = response.entries.map(entryToRecord);
        totalItems.value = response.totalMatches;
        items.value = result;
        formatRows();
        return result;
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
        return [];
    } finally {
        isBusy.value = false;
    }
}

function filterByMode(results: RemoteEntry[]): RemoteEntry[] {
    if (!fileMode.value) {
        // In directory mode, only show directories
        return results.filter((item) => item.class === "Directory");
    }
    return results;
}

function entryToRecord(entry: RemoteEntry): SelectionItem {
    const result = {
        id: entry.uri,
        label: entry.name,
        time: entry.class === "File" ? entry.ctime : "",
        details: entry.class === "File" ? entry.ctime : "",
        isLeaf: entry.class === "File",
        url: entry.uri,
        size: entry.class === "File" ? entry.size : 0,
        entry: entry,
    };
    return result;
}

/** select all files in current folder**/
function onSelectAll() {
    if (!urlTracker.current.value) {
        return;
    }
    // a paginated folder shows one page, so select all toggles that page and keeps the other pages' selection
    const isUnselectAll = isPaginated.value
        ? items.value.some(isRowSelected)
        : selectionModel.value.pathExists(urlTracker.current.value.url);

    for (const item of items.value) {
        if (isUnselectAll) {
            if (isRowSelected(item)) {
                item.isLeaf ? selectionModel.value.add(item) : selectDirectoryRecursive(item);
            }
        } else {
            item.isLeaf ? selectionModel.value.add(item) : selectDirectoryRecursive(item);
        }
    }

    if (isPaginated.value) {
        if (isUnselectAll) {
            // the folder is no longer selected as a whole, but files on its other pages stay selected
            unselectPath(urlTracker.current.value.url, true);
        }
    } else if (!isUnselectAll && items.value.length !== 0) {
        selectedDirectories.value.push(urlTracker.current.value);
    } else if (isDirectorySelected(urlTracker.current.value.id)) {
        selectDirectoryRecursive(urlTracker.current.value);
    }

    hasValue.value = selectionModel.value.count() > 0;
    formatRows();
}

/** Called when selection is complete, values are formatted and parsed to external callback **/
function finalize() {
    const results = selectionModel.value.finalize();
    modalShow.value = false;
    props.callback(results);
}

function onOk() {
    if (!fileMode.value && urlTracker.current.value) {
        selectSingleRecord(urlTracker.current.value);
    }
    finalize();
}

function pushToPropRouter(route: string) {
    if (props.routePush) {
        modalShow.value = false;
        props.routePush(route);
    }
}

function onGoBack(record?: SelectionItem) {
    const { popped } = urlTracker.backwardWithContext();

    load();

    if (popped) {
        selectionDialog.value?.resetPagination(popped.parentPage);
    }
}

// the table drops page and filter changes while busy, so list the current page again once listings finish
watch(
    () => pendingListings.value === 0,
    async (allListed) => {
        if (allListed && itemsProvider.value) {
            await nextTick();
            selectionDialog.value?.refresh();
        }
    },
);

watch(query, () => {
    selectionDialog.value?.resetPagination(1);
});

onMounted(() => {
    if (props.selectedItem) {
        urlTracker.forward(props.selectedItem);
        loadRdmUriRoots();
    }
    load();
});
</script>

<template>
    <SelectionDialog
        ref="selectionDialog"
        :disable-ok="okButtonDisabled"
        :error-message="errorMessage"
        :file-mode="fileMode"
        :fields="fields"
        :is-busy="isBusy || pendingListings > 0"
        :items="items"
        :items-provider="itemsProvider"
        :total-items="totalItems"
        :modal-show="modalShow"
        :modal-static="modalStatic"
        :multiple="multiple"
        :options-show="optionsShow"
        :select-all-variant="selectAllIcon"
        :show-select-icon="undoShow && multiple"
        :undo-show="undoShow"
        :watch-on-page-changes="false"
        @onCancel="() => (modalShow = false)"
        @onClick="clicked"
        @onOk="onOk"
        @onOpen="open"
        @onSelectAll="onSelectAll"
        @onUndo="onGoBack">
        <template v-slot:helper>
            <BAlert v-if="showFTPHelper && isConfigLoaded" id="helper" variant="info" show>
                This Galaxy server allows you to upload files via FTP. To upload some files, log in to the FTP server at
                <strong>{{ config.ftp_upload_site }}</strong> using your Galaxy credentials. For help visit the
                <a href="https://galaxyproject.org/ftp-upload/" target="_blank">tutorial</a>.
                <span v-if="config.enable_oidc"
                    ><br />If you are signed-in to Galaxy using a third-party identity and you
                    <strong>do not have a Galaxy password</strong> please use the reset password option in the login
                    form with your email to create a password for your account.</span
                >
            </BAlert>
            <BAlert v-if="isAtRdmRepositoryRoot" id="rdm-root-helper" variant="info" show>
                This repository has no files at its top level. Open one of the folders below to select it.
            </BAlert>
        </template>
        <template v-slot:buttons>
            <GButton
                v-if="canCreateNewFileSource"
                tooltip
                size="small"
                title="Create a new remote file source"
                data-description="create new file source button"
                @click="pushToPropRouter('/file_source_instances/create')">
                <FontAwesomeIcon :icon="faPlus" />
                Create new
            </GButton>
        </template>
    </SelectionDialog>
</template>
