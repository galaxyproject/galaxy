<template>
    <div v-if="dataset">
        <div v-if="!isEditMode">
            <LibraryBreadcrumb :current-id="dataset_id" :full_path="dataset.full_path" />
            <!-- top bar icons -->
            <b-button title="Download dataset" class="mr-1 mb-2" @click="download(datasetDownloadFormat, dataset_id)">
                <font-awesome-icon icon="download" /> Download
            </b-button>
            <b-button @click="importToHistory" title="Import dataset into history" class="mr-1 mb-2">
                <font-awesome-icon icon="book" />
                to History
            </b-button>
            <b-button
                v-if="dataset.can_user_modify"
                @click="isEditMode = true"
                title="Modify library item"
                class="mr-1 mb-2"
            >
                <font-awesome-icon icon="pencil-alt" />
                Modify
            </b-button>
            <b-button
                v-if="dataset.can_user_modify"
                title="Attempt to detect the format of dataset"
                @click="detectDatatype"
                class="mr-1 mb-2"
            >
                <font-awesome-icon icon="redo" />
                Auto-detect datatype
            </b-button>
            <b-button
                title="Manage permissions"
                v-if="dataset.can_user_manage"
                class="mr-1 mb-2"
                :to="{
                    name: `LibraryFolderDatasetPermissions`,
                    params: { folder_id: folder_id, dataset_id: dataset_id },
                }"
            >
                <font-awesome-icon icon="users" />
                Permissions
            </b-button>
        </div>
        <div v-if="dataset.is_unrestricted">
            This dataset is unrestricted so everybody with the link can access it.
            <copy-to-clipboard
                message="A link to current dataset was copied to your clipboard"
                :text="currentRouteName"
                title="Copy link to this dataset "
            />
        </div>
        <b-table class="mt-2" v-if="table_items" :fields="fields" :items="table_items" thead-class="d-none" striped>
            <template v-slot:cell(name)="row">
                <strong> {{ row.item.name }}</strong>
            </template>
            <template v-slot:cell(value)="row">
                {{ debug(row.item) }}
                <div v-if="isEditMode">
                    <b-form-select
                        :options="types"
                        v-model="modifiedDataset.file_ext"
                        v-if="row.item.name === fieldTitles.file_ext"
                    />
                    <b-form-textarea v-else :value="row.item.value" />
                </div>
                <div v-else>
                    <div>{{ row.item.value }}</div>
                </div>
            </template>
        </b-table>

        <div v-if="dataset.peek" v-html="dataset.peek" />

        <b-button @click="isEditMode = false" v-if="isEditMode">
            <font-awesome-icon :icon="['fas', 'times']" />
            Cancel
        </b-button>
        <b-button @click="updateDataset" v-if="isEditMode">
            <font-awesome-icon :icon="['far', 'save']" />
            Save
        </b-button>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faUsers, faRedo, faPencilAlt, faBook, faDownload, faTimes } from "@fortawesome/free-solid-svg-icons";
import { faSave } from "@fortawesome/free-regular-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
import mod_import_dataset from "components/Libraries/LibraryFolder/TopToolbar/import-to-history/import-dataset";

import { Services } from "components/Libraries/LibraryFolder/services";
import LibraryBreadcrumb from "components/Libraries/LibraryFolder/LibraryBreadcrumb";
import download from "components/Libraries/LibraryFolder/TopToolbar/download";
import CopyToClipboard from "components/CopyToClipboard";
import { Toast } from "ui/toast";
import { fieldsTitles } from "components/Libraries/LibraryFolder/LibraryFolderDataset/constants";

library.add(faUsers, faRedo, faBook, faDownload, faPencilAlt, faTimes, faSave);

function buildFields(fieldTitles, data) {
    return Object.entries(fieldTitles).flatMap(([property, title]) =>
        data[property] ? { name: title, value: data[property] } : []
    );
}
export default {
    props: {
        dataset_id: {
            type: String,
            required: true,
        },
        folder_id: {
            type: String,
            required: true,
        },
    },
    components: {
        LibraryBreadcrumb,
        CopyToClipboard,
        FontAwesomeIcon,
    },
    data() {
        return {
            fieldTitles: fieldsTitles,
            dataset: undefined,
            currentRouteName: window.location.href,
            datasetDownloadFormat: "uncompressed",
            download: download,
            table_items: [],
            types: [],
            modifiedDataset: {},
            isEditMode: false,
            fields: [{ key: "name" }, { key: "value" }],
        };
    },
    created() {
        this.services = new Services({ root: this.root });
        this.services.getDataset(this.dataset_id).then((response) => {
            this.init(response);
        });
        this.services.getDatatypes().then((response) => {
            this.types = response;
            this.types.unshift("auto");
        });
    },
    methods: {
        detectDatatype() {
            this.services.updateDataset(
                this.dataset_id,
                { file_ext: "auto" },
                (response) => {
                    this.init(response);
                    Toast.success("Changes to library dataset saved.");
                },
                (error) => Toast.success(error)
            );
        },
        updateDataset() {
            this.services.updateDataset(
                this.dataset_id,
                this.modifiedDataset,
                (response) => {
                    this.init(response);
                    Toast.success("Changes to library dataset saved.");
                },
                (error) => Toast.success(error)
            );
            this.isEditMode = false;
        },
        importToHistory() {
            new mod_import_dataset.ImportDatasetModal({
                selected: { dataset_ids: [this.dataset_id] },
            });
        },
        debug(e) {
            // console.log(e);
        },
        init(data) {
            this.dataset = data;
            Object.assign(this.modifiedDataset, this.dataset);
            this.table_items = buildFields(this.fieldTitles, this.dataset);
        },
        // parseTypes(raw) {
        //     const types = [];
        //     for (var key in raw) {
        //         types.push({
        //             value: raw[key].extension,
        //         });
        //     }
        //     types.sort((a, b) => (a.id > b.id ? 1 : a.id < b.id ? -1 : 0));
        //     types.unshift("auto");
        //     return types;
        // },
    },
};
</script>
