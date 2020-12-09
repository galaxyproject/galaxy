<template>
    <div>
        <b-breadcrumb>
            <b-breadcrumb-item title="Return to the list of libraries" :href="getHomeUrl">
                Libraries
            </b-breadcrumb-item>
            <template v-for="path_item in this.metadata.full_path">
                <b-breadcrumb-item
                    :key="path_item[0]"
                    :title="isCurrentFolder(path_item[0]) ? `You are in this folder` : `Return to this folder`"
                    :active="isCurrentFolder(path_item[0])"
                    @click="changeFolderId(path_item[0])"
                    href="#"
                    >{{ path_item[1] }}</b-breadcrumb-item
                >
            </template>
        </b-breadcrumb>

        <div class="form-inline d-flex align-items-center mb-2">
            <a class="mr-1 btn btn-secondary" :href="getHomeUrl" data-toggle="tooltip" title="Go to first page">
                <font-awesome-icon icon="home" />
            </a>
            <div>
                <div class="form-inline">
                    <SearchField @updateSearch="updateSearch($event)"></SearchField>
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
                    <div v-if="metadata.can_add_library_item">
                        <div
                            title="Add datasets to current folder"
                            class="dropdown add-library-items add-library-items-datasets mr-1"
                        >
                            <button type="button" class="btn btn-secondary dropdown-toggle" data-toggle="dropdown">
                                <span class="fa fa-plus"></span> Datasets <span class="caret" />
                            </button>
                            <div class="dropdown-menu">
                                <a class="dropdown-item cursor-pointer" @click="addDatasets('history')">
                                    from History</a
                                >
                                <a
                                    v-if="user_library_import_dir"
                                    class="dropdown-item cursor-pointer"
                                    @click="addDatasets('userdir')"
                                >
                                    from User Directory
                                </a>
                                <div v-if="library_import_dir || allow_library_path_paste">
                                    <h5 class="dropdown-header cursor-pointer">Admins only</h5>
                                    <a
                                        v-if="library_import_dir"
                                        class="dropdown-item cursor-pointer"
                                        @click="addDatasets('importdir')"
                                    >
                                        from Import Directory
                                    </a>
                                    <a
                                        v-if="allow_library_path_paste"
                                        class="dropdown-item cursor-pointer"
                                        @click="addDatasets('path')"
                                    >
                                        from Path
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="dropdown mr-1">
                        <button
                            type="button"
                            class="primary-button dropdown-toggle add-to-history"
                            data-toggle="dropdown"
                        >
                            <font-awesome-icon icon="book" />
                            Export to History <span class="caret"></span>
                        </button>
                        <div class="dropdown-menu" role="menu">
                            <a
                                href="javascript:void(0)"
                                role="button"
                                class="toolbtn-bulk-import add-to-history-datasets dropdown-item"
                                @click="importToHistoryModal(false)"
                            >
                                as Datasets
                            </a>
                            <a
                                href="javascript:void(0)"
                                role="button"
                                class="toolbtn-collection-import add-to-history-collection dropdown-item"
                                @click="importToHistoryModal(true)"
                            >
                                as a Collection
                            </a>
                        </div>
                    </div>
                    <div
                        title="Download items as archive"
                        class="dropdown dataset-manipulation mr-1"
                        v-if="dataset_manipulation"
                    >
                        <button
                            type="button"
                            id="download-dropdown-btn"
                            class="primary-button dropdown-toggle"
                            data-toggle="dropdown"
                        >
                            <font-awesome-icon icon="download" />
                            Download <span class="caret"></span>
                        </button>
                        <div class="dropdown-menu" role="menu">
                            <a class="dropdown-item cursor-pointer" @click="downloadData('tgz')">.tar.gz</a>
                            <a class="dropdown-item cursor-pointer" @click="downloadData('tbz')">.tar.bz</a>
                            <a class="dropdown-item cursor-pointer" @click="downloadData('zip')">.zip</a>
                        </div>
                    </div>
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
                            @input="toggle_include_deleted($event)"
                            name="checkbox-1"
                        >
                            include deleted
                        </b-form-checkbox>
                    </div>
                </div>
            </div>
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
import mod_import_dataset from "./import-to-history/import-dataset";
import mod_import_collection from "./import-to-history/import-collection";
import mod_add_datasets from "./add-datasets";
import { Toast } from "ui/toast";
import download from "./download";
import mod_utils from "utils/utils";
import { getAppRoot } from "onload/loadConfig";
import SearchField from "../SearchField";
import { Services } from "../services";

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
        isAllSelectedMode: {
            type: Boolean,
            required: true,
        },
        selected: {
            type: Array,
            required: true,
        },
        unselected: {
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
        SearchField,
        FontAwesomeIcon,
    },
    data() {
        return {
            is_admin: false,
            user_library_import_dir: false,
            library_import_dir: false,
            allow_library_path_paste: false,
            list_genomes: [],
            list_extensions: [],
            // datatype placeholder for extension auto-detection
            auto: {
                id: "auto",
                text: "Auto-detect",
                description: `This system will try to detect the file type automatically.
                     If your file is not detected properly as one of the known formats,
                     it most likely means that it has some format problems (e.g., different
                     number of columns on different rows). You can still coerce the system
                     to set your data to the format you think it should be.
                     You can also upload compressed files, which will automatically be decompressed`,
            },
        };
    },
    created() {
        const Galaxy = getGalaxyInstance();
        this.services = new Services();
        this.is_admin = Galaxy.user.attributes.is_admin;
        this.user_library_import_dir = Galaxy.config.user_library_import_dir;
        this.library_import_dir = Galaxy.config.library_import_dir;
        this.allow_library_path_paste = Galaxy.config.allow_library_path_paste;

        this.fetchExtAndGenomes();
    },
    computed: {
        contains_file_or_folder: function () {
            return this.folderContents.find((el) => el.type === "folder" || el.type === "file");
        },
        logged_dataset_manipulation: function () {
            const Galaxy = getGalaxyInstance();
            // logic from legacy code
            return !!(this.contains_file_or_folder && Galaxy.user && !Galaxy.user.isAnonymous());
        },
        dataset_manipulation: function () {
            const Galaxy = getGalaxyInstance();
            // logic from legacy code
            return !!(this.contains_file_or_folder && Galaxy.user);
        },

        getHomeUrl: () => {
            return `${getAppRoot()}library/list`;
        },
        allDatasets: function () {
            return this.folderContents.filter((element) => element.type === "file");
        },
    },
    methods: {
        updateSearch: function (value) {
            this.$emit("updateSearch", value);
        },
        changeFolderId: function (value) {
            this.$emit("changeFolderId", value);
        },
        deleteSelected: function () {
            this.getSelected().then((selected) =>
                deleteSelectedItems(
                    selected,
                    (deletedItem) => this.$emit("deleteFromTable", deletedItem),
                    () => this.$emit("refreshTable"),
                    () => this.$emit("refreshTableContent")
                )
            );
        },
        async getSelected() {
            if (this.isAllSelectedMode) {
                this.$emit("setBusy", true);
                const selected = await this.services.getFilteredFolderContents(this.folder_id, this.unselected);
                this.$emit("setBusy", false);
                return selected;
            } else return this.selected;
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
        downloadData(format) {
            this.findCheckedItems().then(({ datasets, folders }) => {
                if (this.selected.length === 0) {
                    Toast.info("You must select at least one dataset to download");
                    return;
                }

                download(format, datasets, folders);
            });
        },
        addDatasets(source) {
            new mod_add_datasets.AddDatasets({
                source: source,
                id: this.folder_id,
                updateContent: this.updateContent,
                list_genomes: this.list_genomes,
                list_extensions: this.list_extensions,
            });
        },
        // helper function to make legacy code compatible
        findCheckedItems: async function (idOnly = true) {
            const datasets = [];
            const folder = [];
            const selected = await this.getSelected();
            selected.forEach((item) => {
                item.type === "file" ? datasets.push(idOnly ? item.id : item) : idOnly ? item.id : item;
            });
            return { datasets: datasets, folders: folder };
        },
        importToHistoryModal: function (isCollection) {
            this.findCheckedItems(!isCollection).then(({ datasets, folders }) => {
                const checkedItems = this.selected;
                checkedItems.dataset_ids = datasets;
                checkedItems.folder_ids = folders;
                if (isCollection) {
                    new mod_import_collection.ImportCollectionModal({
                        selected: checkedItems,
                        allDatasets: this.allDatasets,
                    });
                } else {
                    new mod_import_dataset.ImportDatasetModal({
                        selected: checkedItems,
                    });
                }
            });
        },
        isCurrentFolder(id) {
            return this.folder_id === id;
        },
        /*
            Slightly adopted Bootstrap code
        */
        /**
         * Request all extensions and genomes from Galaxy
         * and save them in sorted arrays.
         */
        fetchExtAndGenomes: function () {
            mod_utils.get({
                url: `${getAppRoot()}api/datatypes?extension_only=False`,
                success: (datatypes) => {
                    this.list_extensions = [];
                    for (const key in datatypes) {
                        this.list_extensions.push({
                            id: datatypes[key].extension,
                            text: datatypes[key].extension,
                            description: datatypes[key].description,
                            description_url: datatypes[key].description_url,
                        });
                    }
                    this.list_extensions.sort((a, b) => (a.id > b.id ? 1 : a.id < b.id ? -1 : 0));
                    this.list_extensions.unshift(this.auto);
                },
                cache: true,
            });
            mod_utils.get({
                url: `${getAppRoot()}api/genomes`,
                success: (genomes) => {
                    this.list_genomes = [];
                    for (const key in genomes) {
                        this.list_genomes.push({
                            id: genomes[key][1],
                            text: genomes[key][0],
                        });
                    }
                    this.list_genomes.sort((a, b) => (a.id > b.id ? 1 : a.id < b.id ? -1 : 0));
                },
                cache: true,
            });
        },
        showDetails() {
            showLocInfo(Object.assign({ id: this.folder_id }, this.metadata));
        },
        toggle_include_deleted: function (value) {
            this.$emit("fetchFolderContents", value);
        },
        updateContent: function () {
            this.$emit("fetchFolderContents");
        },
    },
};
</script>

<style scoped>
@import "./pointer.css";
</style>
