<template>
    <div>
        <FolderTopBar
            :search-text="searchText"
            :can-add-library-item="canAddLibraryItem"
            :folder-contents="folderContents"
            :include-deleted.sync="includeDeleted"
            :folder-id="currentFolderId"
            :selected="selected"
            :metadata="folder_metadata"
            :unselected="unselected"
            :is-all-selected-mode="isAllSelectedMode"
            @updateSearch="updateSearchValue($event)"
            @refreshTable="refreshTable"
            @refreshTableContent="refreshTableContent"
            @fetchFolderContents="fetchFolderContents($event)"
            @deleteFromTable="deleteFromTable"
            @setBusy="setBusy($event)"
            @newFolder="newFolder" />
        <b-table
            id="folder_list_body"
            ref="folder_content_table"
            striped
            hover
            :busy.sync="isBusy"
            :fields="fields"
            :items="folderContents"
            :per-page="perPage"
            selectable
            no-select-on-click
            show-empty
            @sort-changed="onSort"
            @row-clicked="onRowClick">
            <template v-slot:empty>
                <div v-if="isBusy" class="text-center my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong>Loading...</strong>
                </div>
                <div v-else class="empty-folder-message">
                    This folder is either empty or you do not have proper access permissions to see the contents. If you
                    expected something to show up please consult the
                    <a href="https://galaxyproject.org/data-libraries/#permissions" target="_blank">
                        library security wikipage
                    </a>
                </div>
            </template>
            <template v-slot:head(selected)="">
                <FontAwesomeIcon
                    v-if="isAllSelectedMode && !isAllSelectedOnPage()"
                    class="select-checkbox cursor-pointer"
                    size="lg"
                    title="Check to select all datasets"
                    icon="minus-square"
                    @click="toggleSelect" />
                <FontAwesomeIcon
                    v-else
                    class="select-checkbox cursor-pointer"
                    size="lg"
                    title="Check to select all datasets"
                    :icon="isAllSelectedOnPage() ? ['far', 'check-square'] : ['far', 'square']"
                    @click="toggleSelect" />
            </template>
            <template v-slot:cell(selected)="row">
                <FontAwesomeIcon
                    v-if="!row.item.isNewFolder && !row.item.deleted"
                    class="select-checkbox lib-folder-checkbox"
                    size="lg"
                    :icon="row.rowSelected ? ['far', 'check-square'] : ['far', 'square']" />
            </template>
            <!-- Name -->
            <template v-slot:cell(name)="row">
                <div v-if="row.item.editMode">
                    <textarea
                        v-if="row.item.isNewFolder"
                        :ref="'name' + row.item.id"
                        v-model="row.item.name"
                        class="form-control"
                        name="input_folder_name"
                        rows="3" />
                    <textarea v-else :ref="'name' + row.item.id" class="form-control" :value="row.item.name" rows="3" />
                </div>
                <div v-else-if="!row.item.deleted">
                    <b-link
                        v-if="row.item.type === 'folder'"
                        :to="{ name: `LibraryFolder`, params: { folder_id: `${row.item.id}` } }">
                        {{ row.item.name }}
                    </b-link>

                    <b-link
                        v-else
                        :to="{
                            name: `LibraryDataset`,
                            params: { folder_id: folder_id, dataset_id: `${row.item.id}` },
                        }">
                        {{ row.item.name }}
                    </b-link>
                </div>
                <!-- Deleted Item-->
                <div v-else>
                    <div class="deleted-item">{{ row.item.name }}</div>
                </div>
            </template>

            <!-- Description -->
            <template v-slot:cell(message)="row">
                <div v-if="row.item.editMode">
                    <textarea
                        v-if="row.item.isNewFolder"
                        :ref="'description' + row.item.id"
                        v-model="row.item.description"
                        class="form-control input_folder_description"
                        rows="3"></textarea>
                    <textarea
                        v-else
                        :ref="'description' + row.item.id"
                        class="form-control input_folder_description"
                        :value="row.item.description"
                        rows="3"></textarea>
                </div>
                <div v-else>
                    <div v-if="getMessage(row.item)" class="description-field">
                        <div
                            v-if="
                                getMessage(row.item).length > maxDescriptionLength &&
                                !expandedMessage.includes(row.item.id)
                            ">
                            <!-- eslint-disable vue/no-v-html -->
                            <span
                                class="shrinked-description"
                                :title="getMessage(row.item)"
                                v-html="linkify(sanitize(getMessage(row.item).substring(0, maxDescriptionLength)))">
                            </span>
                            <!-- eslint-enable vue/no-v-html -->
                            <span :title="getMessage(row.item)"> ...</span>
                            <a class="more-text-btn" href="javascript:void(0)" @click="expandMessage(row.item)">
                                (more)
                            </a>
                        </div>
                        <!-- eslint-disable-next-line vue/no-v-html -->
                        <div v-else v-html="linkify(sanitize(getMessage(row.item)))"></div>
                    </div>
                </div>
            </template>
            <template v-slot:cell(type_icon)="row">
                <FontAwesomeIcon v-if="row.item.type === 'folder'" :icon="['far', 'folder']" title="Folder" />
                <FontAwesomeIcon v-else-if="row.item.type === 'file'" title="Dataset" :icon="['far', 'file']" />
            </template>
            <template v-slot:cell(type)="row">
                <div v-if="row.item.type === 'folder'">{{ row.item.type }}</div>
                <div v-else-if="row.item.type === 'file'">{{ row.item.file_ext }}</div>
            </template>
            <template v-slot:cell(raw_size)="row">
                <div v-if="row.item.type === 'file'" v-html="bytesToString(row.item.raw_size)"></div>
            </template>
            <template v-slot:cell(state)="row">
                <div v-if="row.item.state != 'ok'">
                    {{ row.item.state }}
                </div>
            </template>
            <template v-slot:cell(update_time)="row">
                <UtcDate v-if="row.item.update_time" :date="row.item.update_time" mode="elapsed" />
            </template>
            <template v-slot:cell(is_unrestricted)="row">
                <FontAwesomeIcon v-if="row.item.is_unrestricted" title="Unrestricted dataset" icon="globe" />
                <FontAwesomeIcon v-else-if="row.item.deleted" title="Marked deleted" icon="ban"></FontAwesomeIcon>
                <FontAwesomeIcon v-else-if="row.item.is_private" title="Private dataset" icon="key" />
                <FontAwesomeIcon
                    v-else-if="row.item.is_private === false && row.item.is_unrestricted === false"
                    title="Restricted dataset"
                    icon="shield-alt" />
            </template>

            <template v-slot:cell(buttons)="row">
                <div v-if="row.item.editMode">
                    <button
                        class="primary-button btn-sm permission_folder_btn save_folder_btn"
                        :title="'save ' + row.item.name"
                        @click="row.item.isNewFolder ? createNewFolder(row.item) : saveChanges(row.item)">
                        <FontAwesomeIcon :icon="['far', 'save']" />
                        Save
                    </button>
                    <button
                        class="primary-button btn-sm permission_folder_btn"
                        title="Discard Changes"
                        @click="toggleEditMode(row.item)">
                        <FontAwesomeIcon :icon="['fas', 'times']" />
                        Cancel
                    </button>
                </div>
                <div v-else>
                    <b-button
                        v-if="row.item.can_manage && !row.item.deleted && row.item.type === 'folder'"
                        data-toggle="tooltip"
                        data-placement="top"
                        size="sm"
                        class="lib-btn permission_folder_btn edit_folder_btn"
                        :title="'Edit ' + row.item.name"
                        @click="toggleEditMode(row.item)">
                        <FontAwesomeIcon icon="pencil-alt" />
                        Edit
                    </b-button>
                    <b-button
                        v-if="currentUser.is_admin"
                        size="sm"
                        class="lib-btn permission_lib_btn"
                        :title="`Permissions of ${row.item.name}`"
                        :to="{ path: `${navigateToPermission(row.item)}` }">
                        <FontAwesomeIcon icon="users" />
                        Manage
                    </b-button>
                    <button
                        v-if="row.item.deleted"
                        :title="'Undelete ' + row.item.name"
                        class="lib-btn primary-button btn-sm undelete_dataset_btn"
                        type="button"
                        @click="undelete(row.item, folder_id)">
                        <FontAwesomeIcon icon="unlock" />
                        Undelete
                    </button>
                </div>
            </template>
        </b-table>
        <!-- hide pagination if the table is loading-->
        <b-container>
            <b-row align-v="center" class="justify-content-md-center">
                <b-col md="auto">
                    <div v-if="isBusy">
                        <b-spinner small type="grow"></b-spinner>
                        <b-spinner small type="grow"></b-spinner>
                        <b-spinner small type="grow"></b-spinner>
                    </div>
                    <b-pagination
                        v-else
                        :value="currentPage"
                        :total-rows="total_rows"
                        :per-page="perPage"
                        aria-controls="folder_list_body"
                        @input="changePage">
                    </b-pagination>
                </b-col>

                <b-col cols="1.5">
                    <table>
                        <tr>
                            <td class="m-0 p-0">
                                <b-form-input
                                    id="paginationPerPage"
                                    v-model="perPage"
                                    class="pagination-input-field"
                                    autocomplete="off"
                                    type="number" />
                            </td>
                            <td class="text-muted ml-1 paginator-text">
                                <span class="pagination-total-pages-text">per page, {{ total_rows }} total</span>
                            </td>
                        </tr>
                    </table>
                </b-col>
            </b-row>
        </b-container>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import { initFolderTableIcons } from "components/Libraries/icons";
import { DEFAULT_PER_PAGE, MAX_DESCRIPTION_LENGTH } from "components/Libraries/library-utils";
import UtcDate from "components/UtcDate";
import { Toast } from "composables/toast";
import { sanitize } from "dompurify";
import linkifyHtml from "linkify-html";
import { getAppRoot } from "onload/loadConfig";
import { mapState } from "pinia";
import Utils from "utils/utils";
import Vue from "vue";

import { useUserStore } from "@/stores/userStore";

import { Services } from "./services";
import { fields } from "./table-fields";
import FolderTopBar from "./TopToolbar/FolderTopBar";

initFolderTableIcons();

Vue.use(BootstrapVue);

function initialFolderState() {
    return {
        canAddLibraryItem: false,
        selected: [],
        unselected: [],
        expandedMessage: [],
        folderContents: [],
        includeDeleted: false,
        isAllSelectedMode: false,
    };
}
export default {
    components: {
        FolderTopBar,
        UtcDate,
        FontAwesomeIcon,
    },
    beforeRouteUpdate(to, from, next) {
        this.getFolder(to.params.folder_id, to.params.page);
        next();
    },
    props: {
        folder_id: {
            type: String,
            required: true,
        },
        page: {
            type: Number,
            default: 1,
            required: false,
        },
    },
    data() {
        return {
            ...initialFolderState(),
            ...{
                currentPage: 1,
                sortBy: "name",
                sortDesc: false,
                searchText: "",
                currentFolderId: null,
                error: null,
                isBusy: false,
                folder_metadata: {},
                fields: fields,
                selectMode: "multi",
                perPage: DEFAULT_PER_PAGE,
                maxDescriptionLength: MAX_DESCRIPTION_LENGTH,
                total_rows: 0,
                root: getAppRoot(),
            },
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
    },
    watch: {
        perPage() {
            this.fetchFolderContents();
        },
        includeDeleted() {
            this.fetchFolderContents();
        },
        sortBy() {
            this.fetchFolderContents();
        },
        sortDesc() {
            this.fetchFolderContents();
        },
    },
    created() {
        this.services = new Services({ root: this.root });
        this.getFolder(this.folder_id, this.page);
    },
    methods: {
        sanitize,
        getFolder(folder_id, page) {
            this.currentFolderId = folder_id;
            this.currentPage = page;
            this.resetData();
            this.fetchFolderContents();
        },
        resetData() {
            const data = initialFolderState();
            Object.keys(data).forEach((k) => (this[k] = data[k]));
        },
        onSort(props) {
            this.sortBy = props.sortBy;
            this.sortDesc = props.sortDesc;
        },
        fetchFolderContents() {
            this.setBusy(true);
            this.services
                .getFolderContents(
                    this.currentFolderId,
                    this.includeDeleted,
                    this.sortBy,
                    this.sortDesc,
                    this.perPage,
                    (this.currentPage ? this.currentPage - 1 : 0) * this.perPage,
                    this.searchText
                )
                .then((response) => {
                    this.folderContents = response.folder_contents;
                    this.folder_metadata = response.metadata;
                    this.canAddLibraryItem = response.metadata.can_add_library_item;
                    this.total_rows = response.metadata.total_rows;
                    if (this.isAllSelectedMode) {
                        this.selected = [];
                        Vue.nextTick(() => {
                            this.selectAllRenderedRows();
                        });
                    } else if (this.selected.length > 0) {
                        Vue.nextTick(() => {
                            this.selected.forEach((row) => this.select_unselect_row_by_id(row.id));
                        });
                    }
                    this.setBusy(false);
                })
                .catch((error) => {
                    this.error = error;
                });
        },
        updateSearchValue(value) {
            this.searchText = value;
            this.folderContents = [];
            this.fetchFolderContents();
        },
        selectAllRenderedRows() {
            this.$refs.folder_content_table.items.forEach((row, index) => {
                if (!row.isNewFolder && !row.deleted && !this.unselected.some((unsel) => unsel.id === row.id)) {
                    this.select_unselect_row(index);
                    if (!this.selected.some((selectedItem) => selectedItem.id === row.id)) {
                        this.selected.push(row);
                    }
                }
            });
        },
        clearRenderedSelectedRows() {
            this.$refs.folder_content_table.clearSelected();
            this.selected = [];
        },
        refreshTable() {
            this.$refs.folder_content_table.refresh();
        },
        refreshTableContent() {
            this.fetchFolderContents();
        },
        deleteFromTable(deletedItem) {
            this.folderContents = this.folderContents.filter((element) => {
                if (element.id !== deletedItem.id) {
                    return element;
                }
            });
        },
        isAllSelectedOnPage() {
            if (!this.$refs.folder_content_table) {
                return false;
            }

            // Since we cannot select new folders, toggle should clear all if all rows match, expect new folders
            let unselectable = 0;

            this.$refs.folder_content_table.computedItems.forEach((row) => {
                if (row.isNewFolder || row.deleted) {
                    unselectable++;
                }
            });

            return this.selected.length + unselectable === this.$refs.folder_content_table.computedItems.length;
        },
        toggleSelect() {
            this.unselected = [];
            if (this.isAllSelectedOnPage()) {
                this.isAllSelectedMode = false;
                this.clearRenderedSelectedRows();
            } else {
                this.isAllSelectedMode = true;
                this.selectAllRenderedRows();
            }
        },
        newFolder() {
            this.folderContents.unshift({
                editMode: true,
                isNewFolder: true,
                type: "folder",
                name: "",
                description: "",
            });
            this.refreshTable();
        },
        onRowClick(row, index, event) {
            // check if exists
            const selected_array_index = this.selected.findIndex((item) => item.id === row.id);
            if (selected_array_index > -1) {
                this.selected.splice(selected_array_index, 1);
                this.select_unselect_row(index, true);
                if (this.isAllSelectedMode) {
                    this.unselected.push(row);
                    if (this.total_rows === this.unselected.length) {
                        // if user presses `selectAll` and unselects everything manually
                        this.isAllSelectedMode = false;
                        this.unselected = [];
                    }
                }
            } else {
                if (!row.isNewFolder && !row.deleted) {
                    this.select_unselect_row(index);
                    this.selected.push(row);
                }
            }
        },
        select_unselect_row_by_id(id, unselect = false) {
            const index = this.$refs.folder_content_table.items.findIndex((row) => row.id === id);
            this.select_unselect_row(index, unselect);
        },
        select_unselect_row(index, unselect = false) {
            if (unselect) {
                this.$refs.folder_content_table.unselectRow(index);
            } else {
                this.$refs.folder_content_table.selectRow(index);
            }
        },
        bytesToString(raw_size) {
            return Utils.bytesToString(raw_size);
        },
        navigateToPermission(element) {
            if (element.type === "file") {
                return `/libraries/folders/${this.folder_id}/dataset/${element.id}/permissions`;
            } else if (element.type === "folder") {
                return `/libraries/folders/${element.id}/permissions`;
            }
        },
        getMessage(element) {
            if (element.type === "file") {
                return element.message;
            } else if (element.type === "folder") {
                return element.description;
            }
        },
        expandMessage(element) {
            this.expandedMessage.push(element.id);
        },
        setBusy(value) {
            this.isBusy = value;
        },
        linkify(raw_text) {
            return linkifyHtml(raw_text);
        },
        toggleEditMode(item) {
            item.editMode = !item.editMode;
            this.folderContents = this.folderContents.filter((item) => {
                if (!item.isNewFolder) {
                    return item;
                }
            });
            this.refreshTable();
        },
        createNewFolder: function (folder) {
            if (!folder.name) {
                Toast.error("Folder's name is missing.");
            } else if (folder.name.length < 3) {
                Toast.warning("Folder name has to be at least 3 characters long.");
            } else {
                this.services.newFolder(
                    {
                        parent_id: this.currentFolderId,
                        name: folder.name,
                        description: folder.description,
                    },
                    (resp) => {
                        folder.id = resp.id;
                        folder.update_time = resp.update_time;
                        folder.editMode = false;
                        folder.can_manage = true;
                        folder.isNewFolder = false;

                        this.refreshTable();
                        Toast.success("Folder created.");
                    },
                    () => {
                        Toast.error("An error occurred.");
                    }
                );
            }
        },
        undelete: function (element, parent_folder) {
            const onError = (response) => {
                const message = `${element.type === "folder" ? "Folder" : "Dataset"}`;
                if (typeof response.responseJSON !== "undefined") {
                    Toast.error(`${message} was not undeleted. ${response.responseJSON.err_msg}`);
                } else {
                    Toast.error(`An error occurred! ${message} was not undeleted. Please try again.`);
                }
            };
            if (element.type === "folder") {
                this.services.undeleteFolder(
                    element,
                    (response) => {
                        element.deleted = response.deleted;
                        this.refreshTable();
                        Toast.success("Folder undeleted.");
                    },
                    onError
                );
            } else {
                this.services.undeleteDataset(
                    element,
                    (response) => {
                        element.deleted = response.deleted;
                        this.refreshTable();
                        Toast.success("Dataset undeleted. Click here to see it.", "", {
                            onclick: function () {
                                window.location = `${getAppRoot()}libraries/folders/${parent_folder}/dataset/${
                                    element.id
                                }`;
                            },
                        });
                    },
                    onError
                );
            }
        },
        changePage(page) {
            this.$router.push({ name: `LibraryFolder`, params: { folder_id: this.folder_id, page: page } });
        },

        /*
         Former Backbone code, adopted to work with Vue
        */
        saveChanges(folder) {
            let is_changed = false;
            const new_name = this.$refs[`name${folder.id}`].value;
            if (new_name && new_name !== folder.name) {
                if (new_name.length > 2) {
                    folder.name = new_name;
                    is_changed = true;
                } else {
                    Toast.warning("Folder name has to be at least 3 characters long.");
                    return;
                }
            }
            const new_description = this.$refs[`description${folder.id}`].value;
            if (typeof new_description !== "undefined" && new_description !== folder.description) {
                folder.description = new_description;
                is_changed = true;
            }
            if (is_changed) {
                this.services.updateFolder(
                    folder,
                    () => {
                        Toast.success("Changes to folder saved.");
                        folder.editMode = false;
                        this.refreshTable();
                    },
                    (error) => {
                        if (error.data && error.data.err_msg) {
                            Toast.error(error.data.err_msg);
                        } else {
                            Toast.error("An error occurred while attempting to update the folder.");
                        }
                    }
                );
            } else {
                Toast.info("Nothing has changed.");
            }
        },
    },
};
</script>

<style scoped>
@import "library-folder-table.css";
</style>
