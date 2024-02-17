<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretLeft } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import Vue, { computed, onMounted, ref } from "vue";

import {
    BrowsableFilesSourcePlugin,
    browseRemoteFiles,
    FileSourceBrowsingMode,
    FilterFileSourcesOptions,
    getFileSources,
    RemoteEntry,
} from "@/api/remoteFiles";
import { UrlTracker } from "@/components/DataDialog/utilities";
import { isSubPath } from "@/components/FilesDialog/utilities";
import { selectionStates } from "@/components/SelectionDialog/selectionStates";
import { useConfig } from "@/composables/config";
import { errorMessageAsString } from "@/utils/simple-error";

import { DirectoryRecord, Model, RecordItem } from "./model";

import DataDialogSearch from "@/components/SelectionDialog/DataDialogSearch.vue";
import DataDialogTable from "@/components/SelectionDialog/DataDialogTable.vue";
import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

library.add(faCaretLeft);

interface FilesDialogProps {
    /** Whether to allow multiple selections */
    multiple?: boolean;
    /** Browsing mode to define the selection behavior */
    mode?: FileSourceBrowsingMode;
    /** Whether to show only writable sources */
    requireWritable?: boolean;
    /** Options to filter the file sources */
    filterOptions?: FilterFileSourcesOptions;
    /** Callback function to be called passing the results when selection is complete */
    callback?: (files: any) => void;
}

const props = withDefaults(defineProps<FilesDialogProps>(), {
    multiple: false,
    mode: "file",
    requireWritable: false,
    filterOptions: undefined,
    callback: () => {},
});

const { config, isConfigLoaded } = useConfig();

const selectionModel = ref<Model>(new Model({ multiple: props.multiple }));

const allSelected = ref(false);
const selectedDirectories = ref<DirectoryRecord[]>([]);
const errorMessage = ref<string>();
const filter = ref();
const items = ref<RecordItem[]>([]);
const modalShow = ref(true);
const optionsShow = ref(false);
const undoShow = ref(false);
const hasValue = ref(false);
const showTime = ref(true);
const showDetails = ref(true);
const isBusy = ref(false);
const currentDirectory = ref<DirectoryRecord>();
const showFTPHelper = ref(false);
const selectAllIcon = ref(selectionStates.unselected);
const urlTracker = ref(new UrlTracker(""));

const fileMode = computed(() => props.mode == "file");
const okButtonDisabled = computed(
    () => (fileMode.value && !hasValue.value) || isBusy.value || (!fileMode.value && urlTracker.value.atRoot())
);

/** Collects selected datasets in value array **/
function clicked(record: RecordItem) {
    // ignore the click during directory mode
    if (!fileMode.value) {
        return;
    }
    if (record.isLeaf) {
        // record is file
        selectSingleRecord(record);
    } else {
        // you cannot select entire root directory
        urlTracker.value.atRoot() ? open(record) : selectDirectoryRecursive(record);
    }
    formatRows();
}

function selectSingleRecord(record: RecordItem, selectOnly = false) {
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

function selectDirectoryRecursive(record: DirectoryRecord) {
    // if directory is `selected` or `mixed` unselect everything
    if (isDirectorySelected(record.id) || selectionModel.value.pathExists(record.url)) {
        unselectPath(record.url, false, record.id);
    } else {
        selectedDirectories.value.push(record);
        // look for subdirectories
        const recursive = true;
        isBusy.value = true;
        browseRemoteFiles(record.url, recursive).then((items) => {
            items.forEach((item) => {
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
            isBusy.value = false;
        });
    }
}

/** Add highlighting for record variations, i.e. datasets vs. libraries/collections **/
function formatRows() {
    const getIcon = (isSelected: boolean, path: string) => {
        if (isSelected) {
            return selectionStates.selected;
        } else {
            return selectionModel.value.pathExists(path) ? selectionStates.mixed : selectionStates.unselected;
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
    if (currentDirectory.value?.url) {
        selectAllIcon.value = getIcon(allSelected.value, currentDirectory.value.url);
    }
}

function isDirectorySelected(directoryId: string): boolean {
    return selectedDirectories.value.some(({ id }) => id === directoryId);
}

/** check if all objects in this folders are selected **/
function checkIfAllSelected(): boolean {
    const isAllSelected =
        Boolean(items.value.length) &&
        items.value.every(({ id }) => selectionModel.value.exists(id) || isDirectorySelected(id));

    if (isAllSelected && currentDirectory.value && !isDirectorySelected(currentDirectory.value.id)) {
        // if all selected, select current folder
        selectedDirectories.value.push(currentDirectory.value);
    }

    return isAllSelected;
}

function open(record: DirectoryRecord) {
    load(record);
}

/** Performs server request to retrieve data records **/
function load(record?: DirectoryRecord) {
    currentDirectory.value = urlTracker.value.getUrl(record);
    showFTPHelper.value = record?.url === "gxftp://";
    filter.value = undefined;
    optionsShow.value = false;
    undoShow.value = !urlTracker.value.atRoot();
    if (urlTracker.value.atRoot() || errorMessage.value) {
        errorMessage.value = undefined;
        getFileSources(props.filterOptions)
            .then((results) => {
                const convertedItems = results
                    .filter((item) => !props.requireWritable || item.writable)
                    .map(fileSourcePluginToRecord);
                items.value = convertedItems;
                formatRows();
                optionsShow.value = true;
                showTime.value = false;
                showDetails.value = true;
            })
            .catch((error) => {
                errorMessage.value = errorMessageAsString(error);
            });
    } else {
        if (!currentDirectory.value) {
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
        browseRemoteFiles(currentDirectory.value?.url, false, props.requireWritable)
            .then((results) => {
                items.value = filterByMode(results).map(entryToRecord);
                formatRows();
                optionsShow.value = true;
                showTime.value = true;
                showDetails.value = false;
            })
            .catch((error) => {
                errorMessage.value = errorMessageAsString(error);
            });
    }
}

function filterByMode(results: RemoteEntry[]): RemoteEntry[] {
    if (!fileMode.value) {
        // In directory mode, only show directories
        return results.filter((item) => item.class === "Directory");
    }
    return results;
}

function entryToRecord(entry: RemoteEntry): RecordItem {
    const result = {
        id: entry.uri,
        label: entry.name,
        time: entry.class === "File" ? entry.ctime : "",
        details: entry.class === "File" ? entry.ctime : "",
        isLeaf: entry.class === "File",
        url: entry.uri,
        labelTitle: entry.uri,
        size: entry.class === "File" ? entry.size : 0,
    };
    return result;
}

function fileSourcePluginToRecord(plugin: BrowsableFilesSourcePlugin): RecordItem {
    const result = {
        id: plugin.id,
        label: plugin.label,
        details: plugin.doc,
        isLeaf: false,
        url: plugin.uri_root,
        labelTitle: plugin.uri_root,
    };
    return result;
}

/** select all files in current folder**/
function toggleSelectAll() {
    if (!currentDirectory.value) {
        return;
    }
    const isUnselectAll = selectionModel.value.pathExists(currentDirectory.value.url);

    for (const item of items.value) {
        if (isUnselectAll) {
            if (selectionModel.value.exists(item.id) || selectionModel.value.pathExists(item.id)) {
                item.isLeaf ? selectionModel.value.add(item) : selectDirectoryRecursive(item);
            }
        } else {
            item.isLeaf ? selectionModel.value.add(item) : selectDirectoryRecursive(item);
        }
    }

    if (!isUnselectAll && items.value.length !== 0) {
        selectedDirectories.value.push(currentDirectory.value);
    } else if (isDirectorySelected(currentDirectory.value.id)) {
        selectDirectoryRecursive(currentDirectory.value);
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

function goBack() {
    // Loading without a record navigates back one level
    load();
}

function onOk() {
    if (!fileMode.value && currentDirectory.value) {
        selectSingleRecord(currentDirectory.value);
    }
    finalize();
}

onMounted(() => {
    load();
});
</script>

<template>
    <SelectionDialog
        :error-message="errorMessage"
        :options-show="optionsShow"
        :modal-show="modalShow"
        :hide-modal="() => (modalShow = false)"
        :back-func="goBack"
        :undo-show="undoShow">
        <template v-slot:search>
            <DataDialogSearch v-model="filter" />
        </template>
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
        </template>
        <template v-slot:options>
            <DataDialogTable
                v-if="optionsShow"
                :items="items"
                :multiple="multiple"
                :filter="filter"
                :select-all-icon="selectAllIcon"
                :show-select-icon="undoShow && multiple"
                :show-details="showDetails"
                :show-time="showTime"
                :is-busy="isBusy"
                @clicked="clicked"
                @open="open"
                @toggleSelectAll="toggleSelectAll" />
        </template>
        <template v-slot:buttons>
            <BButton v-if="undoShow" id="back-btn" size="sm" class="float-left" @click="load()">
                <FontAwesomeIcon :icon="['fas', 'caret-left']" />
                Back
            </BButton>
            <BButton
                v-if="multiple || !fileMode"
                id="ok-btn"
                size="sm"
                class="float-right ml-1 file-dialog-modal-ok"
                variant="primary"
                :disabled="okButtonDisabled"
                @click="onOk">
                {{ fileMode ? "Ok" : "Select this folder" }}
            </BButton>
        </template>
    </SelectionDialog>
</template>
