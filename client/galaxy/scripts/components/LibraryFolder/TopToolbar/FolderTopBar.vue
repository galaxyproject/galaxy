<template>
    <div class="form-inline d-flex align-items-center mb-2">
        <a class="mr-1 btn btn-secondary" href="/library/list" data-toggle="tooltip" title="Go to first page">
            <font-awesome-icon icon="home" />
        </a>
        <div>
            <form class="form-inline">
                <b-input-group size="sm">
                    <b-form-input
                        class="mr-1"
                        v-on:input="updateSearch($event)"
                        type="search"
                        id="filterInput"
                        placeholder="Search"
                    >
                        >
                    </b-form-input>
                </b-input-group>
                <button
                    v-if="metadata.can_add_library_item"
                    title="Create new folder"
                    class="btn btn-secondary toolbtn-create-folder add-library-items add-library-items-folder mr-1"
                    type="button"
                    @click="newFolder"
                >
                    <font-awesome-icon icon="plus" />
                    Folder
                </button>
                <button
                    v-if="logged_dataset_manipulation"
                    data-toggle="tooltip"
                    title="Mark items deleted"
                    class="primary-button toolbtn-bulk-delete logged-dataset-manipulation mr-1"
                    type="button"
                    @click="deleteSelected"
                >
                    <font-awesome-icon icon="trash" />
                    Delete
                </button>
                <span class="mr-1" data-toggle="tooltip" title="Show location details">
                    <button @click="showDetails" class="primary-button toolbtn-show-locinfo" type="button">
                        <font-awesome-icon icon="info-circle" />
                        Details
                    </button>
                </span>
                <div class="form-check logged-dataset-manipulation mr-1" v-if="logged_dataset_manipulation">
                    <b-form-checkbox
                        id="checkbox-1"
                        :checked="include_deleted"
                        v-on:input="toggle_include_deleted($event)"
                        name="checkbox-1"
                    >
                        include deleted
                    </b-form-checkbox>
                </div>
            </form>
        </div>
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import { getGalaxyInstance } from "app";
import Vue from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { showLocInfo } from "./details-modal";
import { deleteSelectedItems } from "./delete-selected";
import { initTopBarIcons } from "components/LibraryFolder/icons";

initTopBarIcons();

Vue.use(BootstrapVue);

export default {
    name: "FolderTopBar",
    props: {
        folder_id: {
            type: String,
            required: true,
        },
        include_deleted: {
            type: Boolean,
            required: true,
        },
        selected: {
            type: Array,
            required: true,
        },
        metadata: {
            type: Object,
            required: true,
        },
        folderContents: {
            type: Array,
            required: true,
        },
    },
    components: {
        FontAwesomeIcon,
    },
    data() {
        return {
            dataset_manipulation: false,
            logged_dataset_manipulation: false,
            is_admin: false,
            multiple_add_dataset_options: false,
            user_library_import_dir: false,
            library_import_dir: false,
        };
    },
    created() {
        const Galaxy = getGalaxyInstance();
        this.is_admin = Galaxy.user.attributes.is_admin;
        this.user_library_import_dir = Galaxy.config.user_library_import_dir;
        this.library_import_dir = Galaxy.config.library_import_dir;
        this.allow_library_path_paste = Galaxy.config.allow_library_path_paste;
        if (
            this.user_library_import_dir !== null ||
            this.allow_library_path_paste !== false ||
            this.library_import_dir !== null
        ) {
            this.multiple_add_dataset_options = true;
        }
        const contains_file_or_folder = this.folderContents.find((el) => el.type === "folder" || el.type === "file");

        // logic from legacy code
        if (contains_file_or_folder) {
            if (Galaxy.user) {
                this.dataset_manipulation = true;
                if (!Galaxy.user.isAnonymous()) {
                    this.logged_dataset_manipulation = true;
                }
            }
        }
    },
    methods: {
        updateSearch: function (value) {
            this.$emit("updateSearch", value);
        },
        deleteSelected: function () {
            deleteSelectedItems(this.selected);
        },
        newFolder() {
            this.folderContents.unshift({
                editMode: true,
                isNewFolder: true,
                type: "folder",
                name: "",
                description: "",
            });
            this.$emit("refreshTable");
        },
        /*
        Slightly adopted Bootstrap code
         */
        showDetails() {
            showLocInfo(Object.assign({ id: this.folder_id }, this.metadata));
        },
        toggle_include_deleted: function (value) {
            this.$emit("fetchFolderContents", value);
        },
    },
};
</script>