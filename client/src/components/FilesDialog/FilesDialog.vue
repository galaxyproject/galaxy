<template>
    <selection-dialog
        :error-message="errorMessage"
        :options-show="optionsShow"
        :modal-show="modalShow"
        :hide-modal="() => (modalShow = false)"
        :back-func="goBack"
        :undo-show="undoShow">
        <template v-slot:search>
            <data-dialog-search v-model="filter" />
        </template>
        <template v-slot:helper>
            <b-alert v-if="showFTPHelper" id="helper" variant="info" show>
                This Galaxy server allows you to upload files via FTP. To upload some files, log in to the FTP server at
                <strong>{{ ftpUploadSite }}</strong> using your Galaxy credentials. For help visit the
                <a href="https://galaxyproject.org/ftp-upload/" target="_blank">tutorial</a>.
                <span v-if="oidcEnabled"
                    ><br />If you are signed-in to Galaxy using a third-party identity and you
                    <strong>do not have a Galaxy password</strong> please use the reset password option in the login
                    form with your email to create a password for your account.</span
                >
            </b-alert>
        </template>
        <template v-slot:options>
            <data-dialog-table
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
            <b-btn v-if="undoShow" id="back-btn" size="sm" class="float-left" @click="load()">
                <font-awesome-icon :icon="['fas', 'caret-left']" />
                Back
            </b-btn>
            <b-btn
                v-if="multiple || !fileMode"
                id="ok-btn"
                size="sm"
                class="float-right ml-1 file-dialog-modal-ok"
                variant="primary"
                :disabled="(fileMode && !hasValue) || isBusy || (!fileMode && urlTracker.atRoot())"
                @click="fileMode ? finalize() : selectLeaf(currentDirectory)">
                {{ fileMode ? "Ok" : "Select this folder" }}
            </b-btn>
        </template>
    </selection-dialog>
</template>

<script>
import Vue from "vue";
import { getGalaxyInstance } from "../../app";
import SelectionDialogMixin from "components/SelectionDialog/SelectionDialogMixin";
import { selectionStates } from "components/SelectionDialog/selectionStates";
import { UrlTracker } from "components/DataDialog/utilities";
import { isSubPath } from "components/FilesDialog/utilities";
import { Services } from "./services";
import { Model } from "./model";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretLeft } from "@fortawesome/free-solid-svg-icons";

library.add(faCaretLeft);
export default {
    components: {
        FontAwesomeIcon,
    },
    mixins: [SelectionDialogMixin],
    props: {
        multiple: {
            type: Boolean,
            default: false,
        },
        mode: {
            type: String,
            default: "file",
            validator: (prop) => ["file", "directory"].includes(prop),
        },
        requireWritable: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            allSelected: false,
            selectedDirectories: [],
            errorMessage: null,
            filter: null,
            items: [],
            modalShow: true,
            optionsShow: false,
            undoShow: false,
            hasValue: false,
            showTime: true,
            showDetails: true,
            isBusy: false,
            currentDirectory: undefined,
            showFTPHelper: false,
            selectAllIcon: selectionStates.unselected,
            ftpUploadSite: getGalaxyInstance()?.config?.ftp_upload_site,
            oidcEnabled: getGalaxyInstance()?.config?.enable_oidc,
        };
    },
    computed: {
        fileMode() {
            return this.mode == "file";
        },
    },
    created: function () {
        this.services = new Services();
        this.urlTracker = new UrlTracker("");
        this.model = new Model({ multiple: this.multiple });
        this.load();
    },
    methods: {
        /** Add highlighting for record variations, i.e. datasets vs. libraries/collections **/
        formatRows() {
            const getIcon = (isSelected, path) => {
                if (isSelected) {
                    return selectionStates.selected;
                } else {
                    return this.model.pathExists(path) ? selectionStates.mixed : selectionStates.unselected;
                }
            };

            this.hasValue = this.model.count() > 0 || this.selectedDirectories.length > 0;
            for (const item of this.items) {
                let _rowVariant = "active";
                if (item.isLeaf || !this.fileMode) {
                    _rowVariant = this.model.exists(item.id) ? "success" : "default";
                }
                // if directory
                else if (!item.isLeaf) {
                    _rowVariant = getIcon(this.isDirectorySelected(item.id), item.url);
                }
                Vue.set(item, "_rowVariant", _rowVariant);
            }
            this.allSelected = this.checkIfAllSelected();
            if (this.currentDirectory.url) {
                this.selectAllIcon = getIcon(this.allSelected, this.currentDirectory.url);
            }
        },
        /** Collects selected datasets in value array **/
        clicked: function (record) {
            // ignore the click during directory mode
            if (!this.fileMode) {
                return;
            }
            if (record.isLeaf) {
                // record is file
                this.selectLeaf(record);
            } else {
                // record is directory
                // you cannot select entire root directory
                this.urlTracker.atRoot() ? this.open(record) : this.selectDirectory(record);
            }
            this.formatRows();
        },
        unselectPath(path, unselectOnlyAboveDirectories = false, unselectId) {
            // unselect directories
            this.selectedDirectories = this.selectedDirectories.filter((directory) => {
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
                this.model.unselectUnderPath(path);
            }
        },
        selectLeaf(file, selectOnly = false) {
            const selected = this.model.exists(file.id);
            if (selected) {
                this.unselectPath(file.url, true);
            }
            if (selectOnly) {
                if (!selected) {
                    this.model.add(file);
                }
            } else {
                this.model.add(file);
            }

            this.hasValue = this.model.count() > 0;
            if (this.multiple) {
                this.formatRows();
            } else {
                this.finalize();
            }
        },
        selectDirectory(record) {
            // if directory is `selected` or `mixed` unselect everything
            if (this.isDirectorySelected(record.id) || this.model.pathExists(record.url)) {
                this.unselectPath(record.url, false, record.id);
            } else {
                this.selectedDirectories.push(record);
                // look for subdirectories
                const recursive = true;
                this.isBusy = true;
                this.services.list(record.url, recursive).then((items) => {
                    items.forEach((item) => {
                        // construct record
                        const sub_record = this.parseItemFileMode(item);
                        if (sub_record.isLeaf) {
                            // select file under this path
                            this.selectLeaf(sub_record, true);
                        } else {
                            // select subdirectory
                            this.selectedDirectories.push(sub_record);
                        }
                    });
                    this.isBusy = false;
                });
            }
        },
        isDirectorySelected(directoryId) {
            return this.selectedDirectories.some(({ id }) => id === directoryId);
        },
        open: function (record) {
            this.load(record);
        },
        /** Called when selection is complete, values are formatted and parsed to external callback **/
        finalize: function () {
            const results = this.model.finalize();
            this.modalShow = false;
            this.callback(results);
        },
        /** check if all objects in this folders are selected **/
        checkIfAllSelected() {
            const isAllSelected =
                this.items.length &&
                this.items.every(({ id }) => this.model.exists(id) || this.isDirectorySelected(id));

            if (isAllSelected && !this.isDirectorySelected(this.currentDirectory.id)) {
                // if all selected, select current folder
                this.selectedDirectories.push(this.currentDirectory);
            }

            return isAllSelected;
        },
        /** select all files in current folder**/
        toggleSelectAll: function () {
            const isUnselectAll = this.model.pathExists(this.currentDirectory.url);

            for (const item of this.items) {
                if (isUnselectAll) {
                    if (this.model.exists(item.id) || this.model.pathExists(item.id)) {
                        item.isLeaf ? this.model.add(item) : this.selectDirectory(item);
                    }
                } else {
                    item.isLeaf ? this.model.add(item) : this.selectDirectory(item);
                }
            }

            if (!isUnselectAll && this.items.length !== 0) {
                this.selectedDirectories.push(this.currentDirectory);
            } else if (this.isDirectorySelected(this.currentDirectory.id)) {
                this.selectDirectory(this.currentDirectory);
            }

            this.hasValue = this.model.count() > 0;
            this.formatRows();
        },
        /** Performs server request to retrieve data records **/
        load: function (record) {
            this.currentDirectory = this.urlTracker.getUrl(record);
            this.showFTPHelper = record?.url === "gxftp://";
            this.filter = null;
            this.optionsShow = false;
            this.undoShow = !this.urlTracker.atRoot();
            if (this.urlTracker.atRoot() || this.errorMessage) {
                this.errorMessage = null;
                this.services
                    .getFileSources()
                    .then((items) => {
                        items = items
                            .filter((item) => !this.requireWritable || item.writable)
                            .map((item) => {
                                return {
                                    id: item.id,
                                    label: item.label,
                                    details: item.doc,
                                    isLeaf: false,
                                    url: item.uri_root,
                                    labelTitle: item.uri_root,
                                };
                            });
                        this.items = items;
                        this.formatRows();
                        this.optionsShow = true;
                        this.showTime = false;
                        this.showDetails = true;
                    })
                    .catch((errorMessage) => {
                        this.errorMessage = errorMessage;
                    });
            } else {
                this.services
                    .list(this.currentDirectory.url)
                    .then((items) => {
                        this.items = this.parseItems(items);
                        this.formatRows();
                        this.optionsShow = true;
                        this.showTime = true;
                        this.showDetails = false;
                    })
                    .catch((errorMessage) => {
                        this.errorMessage = errorMessage;
                    });
            }
        },
        goBack() {
            // Loading without a record navigates back one level
            this.load();
        },
        parseItemFileMode(item) {
            const result = {
                id: item.uri,
                label: item.name,
                time: item.ctime,
                isLeaf: item.class === "File",
                size: item.size,
                url: item.uri,
                labelTitle: item.uri,
            };
            return result;
        },
        parseItems(items) {
            if (this.fileMode) {
                items = items.map((item) => {
                    return this.parseItemFileMode(item);
                });
            } else {
                items = items
                    .filter((item) => item.class == "Directory")
                    .map((item) => {
                        return {
                            id: item.uri,
                            label: item.name,
                            time: item.ctime,
                            isLeaf: false,
                            size: item.size,
                            url: item.uri,
                            labelTitle: item.uri,
                        };
                    });
            }
            return items;
        },
    },
};
</script>
