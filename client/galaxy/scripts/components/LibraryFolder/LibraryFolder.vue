<template>
    <div>
        <div v-if="!hasLoaded" class="d-flex justify-content-center m-5">
            <font-awesome-icon icon="spinner" spin size="9x" />
        </div>
        <div v-else>
            <FolderTopBar
                @updateSearch="updateSearchValue($event)"
                @refreshTable="refreshTable"
                :folderContents="this.folderContents"
                :folder_id="folder_id"
                :selected="selected"
                :metadata="folder_metadata"
            ></FolderTopBar>
            <b-table
                id="folder-table"
                striped
                hover
                :filter="filter"
                :filterIncludedFields="filterOn"
                :fields="fields"
                :items="folderContents"
                :per-page="perPage"
                :current-page="currentPage"
                selectable
                :select-mode="selectMode"
                @row-selected="onRowSelected"
                ref="folder_content_table"
                @filtered="onFiltered"
                show-empty
            >
                <template v-slot:empty="">
                    <div class="empty-folder-text">
                        This folder is either empty or you do not have proper access permissions to see the contents. If
                        you expected something to show up please consult the
                        <a href="https://galaxyproject.org/data-libraries/#permissions" target="_blank">
                            library security wikipage
                        </a>
                    </div>
                </template>
                <template v-slot:head(selected)="">
                    <span class="select-all-symbl" @click="toggleSelect">&check;</span>
                </template>
                <template v-slot:cell(selected)="{ rowSelected }">
                    <template v-if="rowSelected">
                        <span aria-hidden="true">&check;</span>
                    </template>
                    <template v-else>
                        <span aria-hidden="true">&nbsp;</span>
                    </template>
                </template>
                <!-- Name -->
                <template v-slot:cell(name)="row">
                    <div v-if="row.item.editMode">
                        <textarea
                            class="form-control"
                            :ref="'name' + row.item.id"
                            :value="row.item.name"
                            rows="3"
                        ></textarea>
                    </div>
                    <div v-else>
                        <a :href="createContentLink(row.item)">{{ row.item.name }}</a>
                    </div>
                </template>

                <!-- Description -->
                <template v-slot:cell(message)="row">
                    <div v-if="row.item.editMode">
                        <textarea
                            class="form-control"
                            :ref="'description' + row.item.id"
                            :value="row.item.description"
                            rows="3"
                        ></textarea>
                    </div>
                    <div v-else>
                        <div class="description-field" v-if="getMessage(row.item)">
                            <div v-if="getMessage(row.item).length > 40 && !expandedMessage.includes(row.item.id)">
                                <span
                                    :title="getMessage(row.item)"
                                    v-html="linkify(getMessage(row.item).substring(0, 40))"
                                >
                                </span>
                                <span :title="getMessage(row.item)"> ...</span>
                                <a class="more-text-btn" @click="expandMessage(row.item)" href="javascript:void(0)"
                                    >(more)</a
                                >
                            </div>
                            <div v-else v-html="linkify(getMessage(row.item))"></div>
                        </div>
                    </div>
                </template>
                <template v-slot:cell(type_icon)="row">
                    <font-awesome-icon v-if="row.item.type === 'folder'" :icon="['far', 'folder']" title="Folder" />
                    <font-awesome-icon v-else-if="row.item.type === 'file'" title="Dataset" :icon="['far', 'file']" />
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
                    <font-awesome-icon v-if="row.item.is_unrestricted" title="Unrestricted dataset" icon="globe" />

                    <font-awesome-icon v-else-if="row.item.is_private" title="Private dataset" icon="key" />
                    <font-awesome-icon
                        v-else-if="row.item.is_private === false && row.item.is_unrestricted === false"
                        title="Restricted dataset"
                        icon="shield-alt"
                    />
                </template>

                <template v-slot:cell(buttons)="row">
                    <div v-if="row.item.editMode">
                        <button
                            @click="row.item.isNewFolder ? createNewFolder(row.item) : saveChanges(row.item)"
                            class="primary-button btn-sm permission_folder_btn"
                            :title="'save ' + row.item.name"
                        >
                            <font-awesome-icon :icon="['far', 'save']" />
                            Save
                        </button>
                        <button
                            class="primary-button btn-sm permission_folder_btn"
                            title="Discard Changes"
                            @click="toggleMode(row.item)"
                        >
                            <font-awesome-icon :icon="['fas', 'times']" />
                            Cancel
                        </button>
                    </div>
                    <div v-else>
                        <a v-if="row.item.can_manage && !row.item.deleted && row.item.type === 'folder'">
                            <button
                                @click="toggleMode(row.item)"
                                data-toggle="tooltip"
                                data-placement="top"
                                class="primary-button btn-sm permission_folder_btn"
                                :title="'Edit ' + row.item.name"
                            >
                                <span class="fa fa-pencil"></span> Edit
                            </button>
                        </a>
                        <a v-if="row.item.can_manage" :href="createPermissionLink(row.item)">
                            <button
                                data-toggle="tooltip"
                                data-placement="top"
                                class="primary-button btn-sm permission_folder_btn"
                                :title="'Permissions of ' + row.item.name"
                            >
                                <span class="fa fa-group"></span> Manage
                            </button>
                        </a>
                    </div>
                </template>
            </b-table>
            <b-container>
                <b-row class="justify-content-md-center">
                    <b-col md="auto">
                        <b-pagination
                            v-model="currentPage"
                            :total-rows="rows"
                            :per-page="perPage"
                            aria-controls="folder-table"
                        >
                        </b-pagination>
                    </b-col>
                    <b-col cols="1.5">
                        <table>
                            <tr>
                                <td class="m-0 p-0">
                                    <b-form-input
                                        class="pagination-input-field"
                                        id="paginationPerPage"
                                        autocomplete="off"
                                        type="number"
                                        v-model="perPage"
                                    />
                                </td>
                                <td class="text-muted ml-1 paginator-text">
                                    <span class="pagination-total-pages-text">per page, {{ rows }} total</span>
                                </td>
                            </tr>
                        </table>
                    </b-col>
                </b-row>
            </b-container>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import UtcDate from "components/UtcDate";
import BootstrapVue from "bootstrap-vue";
import { Services } from "./services";
import Utils from "utils/utils";
import linkify from "linkifyjs/html";
import { fields } from "./table-fields";
import { Toast } from "ui/toast";
import FolderTopBar from "./TopToolbar/FolderTopBar";
import { initFolderTableIcons } from "./icons.js";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

initFolderTableIcons();

Vue.use(BootstrapVue);

export default {
    props: {
        folder_id: {
            type: String,
            required: true,
        },
    },
    components: {
        FolderTopBar,
        UtcDate,
        FontAwesomeIcon,
    },
    data() {
        return {
            error: null,
            folder_metadata: null,
            currentPage: 1,
            fields: fields,
            selectMode: "multi",
            selected: [],
            expandedMessage: [],
            folderContents: [],
            hasLoaded: false,
            perPage: 15,
            filter: null,
            filterOn: [],
            is_admin: false,
            multiple_add_dataset_options: false,
            user_library_import_dir: false,
            library_import_dir: false,
        };
    },
    computed: {
        rows() {
            return this.folderContents.length;
        },
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.services
            .getFolderContents(this.folder_id)
            .then((response) => {
                response.folder_contents.forEach(
                    (content) => (content.update_time = new Date(content.update_time).toISOString())
                );
                this.folderContents = response.folder_contents;
                this.folder_metadata = response.metadata;
                this.hasLoaded = true;
                console.log(response);
            })
            .catch((error) => {
                this.error = error;
            });
    },
    methods: {
        updateSearchValue(value) {
            this.filter = value;
        },
        selectAllRows() {
            this.$refs.folder_content_table.selectAllRows();
        },
        clearSelected() {
            this.$refs.folder_content_table.clearSelected();
        },
        refreshTable() {
            this.$refs.folder_content_table.refresh();
        },
        toggleSelect() {
            // Since we cannot select new folders, toggle should clear all if all rows match, expect new folders
            let newFoldersCounter = 0
            this.folderContents.forEach(row=>{
                if(row.isNewFolder)
                    newFoldersCounter++
            })

            if (this.selected.length + newFoldersCounter !== this.rows ) {
                this.selectAllRows();
            } else {
                this.clearSelected();
            }
        },
        onRowSelected(items) {
            // make new folders not selectable
            // https://github.com/bootstrap-vue/bootstrap-vue/issues/3134#issuecomment-526810892
            for (let i = 0; i < items.length; i++) {
                if(items[i].isNewFolder)
                     this.$refs.folder_content_table.unselectRow(i)
            }
            this.selected = items;
        },
        bytesToString(raw_size) {
            return Utils.bytesToString(raw_size);
        },
        createContentLink(element) {
            if (element.type === "file")
                return `${this.root}library/list#folders/${this.folder_id}/datasets/${element.id}`;
            else if (element.type === "folder") return `${this.root}library/folders/${element.id}`;
        },
        createPermissionLink(element) {
            if (element.type === "file") return `${this.createContentLink(element)}/permissions`;
            else if (element.type === "folder") return `${this.root}library/list#folders/${element.id}/permissions`;
        },
        getMessage(element) {
            if (element.type === "file") return element.message;
            else if (element.type === "folder") return element.description;
        },
        expandMessage(element) {
            this.expandedMessage.push(element.id);
        },
        linkify(raw_text) {
            return linkify(raw_text);
        },
        toggleMode(item) {
            item.editMode = !item.editMode;
            this.folderContents = this.folderContents.filter((item) => {
                if (!item.isNewFolder) return item;
            });
            this.refreshTable();
        },
        onFiltered(filteredItems) {
            // Trigger pagination to update the number of buttons/pages due to filtering
            this.totalRows = filteredItems.length;
            this.currentPage = 1;
        },
        createNewFolder: function (folder) {
            const name = this.$refs[`name${folder.id}`].value;
            const description = this.$refs[`description${folder.id}`].value;
            if (!name) {
                Toast.error("Folder's name is missing.");
            } else if (name.length < 3) {
                Toast.warning("Folder name has to be at least 3 characters long.");
            } else {
                this.services.newFolder(
                    {
                        parent_id: this.folder_id,
                        name: name,
                        description: description,
                    },
                    (resp) => {
                        folder.id = resp.id;
                        folder.name = name;
                        folder.description = description;
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
        /*
         Former Backbone code, adopted to work with Vue
        */
        saveChanges(folder) {
            let is_changed = false;
            const new_name = this.$refs[`name${folder.id}`].value;
            if (typeof new_name !== "undefined" && new_name !== folder.name) {
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
