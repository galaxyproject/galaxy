<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretLeft } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import Vue, { computed, onMounted, ref } from "vue";

import { UrlTracker } from "@/components/DataDialog/utilities";
import { isSubPath } from "@/components/FilesDialog/utilities";
import { selectionStates } from "@/components/SelectionDialog/selectionStates";
import { errorMessageAsString } from "@/utils/simple-error";

import { getGalaxyInstance } from "../../app";
import { Model } from "./model";
import { browseRemoteFiles, FilesSourcePlugin, getFileSources, RemoteEntry } from "./services";

import DataDialogSearch from "@/components/SelectionDialog/DataDialogSearch.vue";
import DataDialogTable from "@/components/SelectionDialog/DataDialogTable.vue";
import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

library.add(faCaretLeft);

interface FilesDialogProps {
    multiple?: boolean;
    mode?: "file" | "directory";
    requireWritable?: boolean;
    callback?: (files: any) => void;
}

interface Record {
    id: string;
    label: string;
    details: string;
    isLeaf: boolean;
    url: string;
    labelTitle: string | undefined;
}

interface FileRecord extends Record {
    isLeaf: true;
}

interface DirectoryRecord extends Record {
    isLeaf: false;
}

const props = withDefaults(defineProps<FilesDialogProps>(), {
    multiple: false,
    mode: "file",
    requireWritable: false,
    callback: () => {},
});

const model = ref<Model>(new Model({ multiple: props.multiple }));

const allSelected = ref(false);
const selectedDirectories = ref<DirectoryRecord[]>([]);
const errorMessage = ref<string>();
const filter = ref();
const items = ref<Record[]>([]);
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
const ftpUploadSite = ref(getGalaxyInstance()?.config?.ftp_upload_site);
const oidcEnabled = ref(getGalaxyInstance()?.config?.enable_oidc);

const urlTracker = ref(new UrlTracker(""));

const fileMode = computed(() => props.mode == "file");

/** Collects selected datasets in value array **/
function clicked(record: Record) {
    // ignore the click during directory mode
    if (!fileMode.value) {
        return;
    }
    if (record.isLeaf) {
        // record is file
        selectLeaf(record as FileRecord);
    } else {
        // record is directory
        const directory = record as DirectoryRecord;
        // you cannot select entire root directory
        urlTracker.value.atRoot() ? open(directory) : selectDirectory(directory);
    }
    formatRows();
}

function selectLeaf(file: FileRecord, selectOnly = false) {
    const selected = model.value.exists(file.id);
    if (selected) {
        unselectPath(file.url, true);
    }
    if (selectOnly) {
        if (!selected) {
            model.value.add(file);
        }
    } else {
        model.value.add(file);
    }

    hasValue.value = model.value.count() > 0;
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
        model.value.unselectUnderPath(path);
    }
}

function selectDirectory(record: DirectoryRecord) {
    // if directory is `selected` or `mixed` unselect everything
    if (isDirectorySelected(record.id) || model.value.pathExists(record.url)) {
        unselectPath(record.url, false, record.id);
    } else {
        selectedDirectories.value.push(record);
        // look for subdirectories
        const recursive = true;
        isBusy.value = true;
        browseRemoteFiles(record.url, recursive).then((items) => {
            items.forEach((item) => {
                // construct record
                const sub_record = entryToRecord(item);
                if (sub_record.isLeaf) {
                    // select file under this path
                    selectLeaf(sub_record as FileRecord, true);
                } else {
                    // select subdirectory
                    selectedDirectories.value.push(sub_record as DirectoryRecord);
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
            return model.value.pathExists(path) ? selectionStates.mixed : selectionStates.unselected;
        }
    };

    hasValue.value = model.value.count() > 0 || selectedDirectories.value.length > 0;
    for (const item of items.value) {
        let _rowVariant = "active";
        if (item.isLeaf || !fileMode.value) {
            _rowVariant = model.value.exists(item.id) ? "success" : "default";
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
        Boolean(items.value.length) && items.value.every(({ id }) => model.value.exists(id) || isDirectorySelected(id));

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
        getFileSources()
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
        browseRemoteFiles(currentDirectory.value?.url)
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

function entryToRecord(entry: RemoteEntry): Record {
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

function fileSourcePluginToRecord(plugin: FilesSourcePlugin): Record {
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
    const isUnselectAll = model.value.pathExists(currentDirectory.value.url);

    for (const item of items.value) {
        if (isUnselectAll) {
            if (model.value.exists(item.id) || model.value.pathExists(item.id)) {
                item.isLeaf ? model.value.add(item) : selectDirectory(item as DirectoryRecord);
            }
        } else {
            item.isLeaf ? model.value.add(item) : selectDirectory(item as DirectoryRecord);
        }
    }

    if (!isUnselectAll && items.value.length !== 0) {
        selectedDirectories.value.push(currentDirectory.value);
    } else if (isDirectorySelected(currentDirectory.value.id)) {
        selectDirectory(currentDirectory.value);
    }

    hasValue.value = model.value.count() > 0;
    formatRows();
}

/** Called when selection is complete, values are formatted and parsed to external callback **/
function finalize() {
    const results = model.value.finalize();
    modalShow.value = false;
    props.callback(results);
}

function goBack() {
    // Loading without a record navigates back one level
    load();
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
            <BAlert v-if="showFTPHelper" id="helper" variant="info" show>
                This Galaxy server allows you to upload files via FTP. To upload some files, log in to the FTP server at
                <strong>{{ ftpUploadSite }}</strong> using your Galaxy credentials. For help visit the
                <a href="https://galaxyproject.org/ftp-upload/" target="_blank">tutorial</a>.
                <span v-if="oidcEnabled"
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
                :disabled="(fileMode && !hasValue) || isBusy || (!fileMode && urlTracker.atRoot())"
                @click="fileMode ? finalize() : selectLeaf(currentDirectory)">
                {{ fileMode ? "Ok" : "Select this folder" }}
            </BButton>
        </template>
    </SelectionDialog>
</template>
