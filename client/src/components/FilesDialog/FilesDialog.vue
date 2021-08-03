<template>
    <selection-dialog
        :error-message="errorMessage"
        :options-show="optionsShow"
        :modal-show="modalShow"
        :hide-modal="() => (modalShow = false)"
    >
        <template v-slot:search>
            <data-dialog-search v-model="filter" />
        </template>
        <template v-if="undoShow && multiple && items.length > 0" v-slot:selectAll>
            <b-button @click="toggleSelectAll()" variant="light">
                <font-awesome-icon icon="th-large" /> {{ `${allSelected ? "Unselect" : "Select"}` }} entire folder
            </b-button>
        </template>
        <template v-slot:options>
            <data-dialog-table
                v-if="optionsShow"
                :items="items"
                :multiple="multiple"
                :filter="filter"
                :show-select-icon="undoShow"
                :show-details="showDetails"
                :show-time="showTime"
                :show-navigate="showNavigate"
                @clicked="clicked"
                @open="open"
                @load="load"
            />
        </template>
        <template v-slot:buttons>
            <b-btn size="sm" class="float-left" v-if="undoShow" @click="load()">
                <div class="fa fa-caret-left mr-1" />
                Back
            </b-btn>
            <b-btn
                v-if="multiple"
                size="sm"
                class="float-right ml-1 file-dialog-modal-ok"
                variant="primary"
                @click="finalize"
                :disabled="!hasValue"
            >
                Ok
            </b-btn>
        </template>
    </selection-dialog>
</template>

<script>
import Vue from "vue";
import SelectionDialogMixin from "components/SelectionDialog/SelectionDialogMixin";
import { selectionModes } from "components/SelectionDialog/selectionModes";
import { UrlTracker } from "components/DataDialog/utilities";
import { Services } from "./services";
import { Model } from "./model";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faThLarge } from "@fortawesome/free-solid-svg-icons";

library.add(faThLarge);
export default {
    mixins: [SelectionDialogMixin],
    props: {
        multiple: {
            type: Boolean,
            default: false,
        },
        mode: {
            type: String,
            default: "file",
            validator: (prop) => ["file", "directory", "tree"].includes(prop),
        },
        requireWritable: {
            type: Boolean,
            default: false,
        },
    },
    components: {
        FontAwesomeIcon,
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
            showSelectIcon: true,
            showNavigate: true,
        };
    },
    created: function () {
        this.services = new Services();
        this.urlTracker = new UrlTracker("");
        this.model = new Model({ multiple: this.multiple });
        this.load();
    },
    computed: {
        fileMode() {
            return this.mode == "file";
        },
    },
    methods: {
        /** Add highlighting for record variations, i.e. datasets vs. libraries/collections **/
        formatRows() {
            this.hasValue = this.model.count() > 0 || this.selectedDirectories.length > 0;

            for (const item of this.items) {
                let _rowVariant = "active";
                if (item.isLeaf || !this.fileMode) {
                    _rowVariant = this.model.exists(item.id) ? "success" : "default";
                }
                // if directory
                else if (!item.isLeaf) {
                    if (this.isDirectorySelected(item.id)) {
                        _rowVariant = selectionModes.selected;
                    } else {
                        _rowVariant = this.model.isPathExists(item.path)
                            ? selectionModes.mixed
                            : selectionModes.unselected;
                    }
                }
                Vue.set(item, "_rowVariant", _rowVariant);
            }
            this.allSelected = this.checkIfAllSelected();
        },
        /** Collects selected datasets in value array **/
        clicked: function (record) {
            if (record.isLeaf || !this.fileMode) {
                // record is file
                this.selectFile(record);
            } else {
                // record is directory
                // you cannot select entire root directory
                this.urlTracker.atRoot() ? this.open(record) : this.selectDirectory(record);
            }
            this.formatRows();
        },
        unselectPath(path, unselectDirectoriesAbove = false, unselectId) {
            // unselect directory and all subdirectories under it
            this.selectedDirectories = this.selectedDirectories.filter((directory) => {
                if (unselectId === directory.id) {
                    return false;
                }
                const pathMatched = unselectDirectoriesAbove ? path.startsWith(directory.path) : directory.path.startsWith(path);
                if (directory.path !== path && pathMatched) {
                    return false;
                }
                return true;
            });
            if (!unselectDirectoriesAbove) {
                // unselect all files under this path
                this.model.finalize().forEach((file) => {
                    if (file.path.startsWith(path)) {
                        this.model.add(file);
                    }
                });
            }
        },
        selectFile(file) {
            if (this.model.exists(file.id)) {
                this.unselectPath(file.path, true);
            }
            this.model.add(file);

            this.hasValue = this.model.count() > 0;
            if (this.multiple) {
                this.formatRows();
            } else {
                this.finalize();
            }
        },
        selectDirectory(record) {
            if (this.isDirectorySelected(record.id)) {
                this.unselectPath(record.path, false, record.id);
            } else {
                this.selectedDirectories.push(record);
                // look for subdirectories
                const recursive = true;
                this.services.list(record.url, recursive).then((items) => {
                    items.forEach((item) => {
                        // construct record
                        const sub_record = this.parseItemFileMode(item);

                        if (sub_record.isLeaf) {
                            // select file under this path
                            this.model.add(sub_record);
                        } else {
                            // select subdirectory
                            this.selectedDirectories.push(sub_record);
                        }
                    });
                });
            }
        },
        isDirectorySelected(directoryId) {
            return this.selectedDirectories.some(({ id }) => id === directoryId);
        },
        open: function (record) {
            this.load(record.url);
        },
        isSelectedUnderPath(path) {},
        /** Called when selection is complete, values are formatted and parsed to external callback **/
        finalize: function () {
            const results = this.model.finalize();
            this.modalShow = false;
            this.callback(results);
        },
        /** check if all objects in this folders are selected **/
        checkIfAllSelected() {
            return this.items.every(({ id }) => this.model.exists(id) || this.isDirectorySelected(id));
        },
        /** select all files in current folder**/
        toggleSelectAll: function () {
            for (const item of this.items) {
                if (this.allSelected) {
                    //  model.add() toggles select. Since all items are selected, we unselect all on this page
                    this.model.add(item);
                    //  add item if it's not added already
                } else if (!this.model.exists(item.id)) {
                    this.model.add(item);
                }
            }
            this.hasValue = this.model.count() > 0;
            this.formatRows();
        },
        /** Performs server request to retrieve data records **/
        load: function (url) {
            url = this.urlTracker.getUrl(url);
            this.filter = null;
            this.optionsShow = false;
            this.undoShow = !this.urlTracker.atRoot();
            if (this.urlTracker.atRoot()) {
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
                    .list(url)
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
        parseItemFileMode(item) {
            const result = {
                id: item.uri,
                label: item.name,
                // remove first and last slash
                path: item.path.replace(/^\/|\/$/g, ""),
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
                            path: item.path.replace(/^\/|\/$/g, ""),
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
