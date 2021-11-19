<template>
    <div v-if="dataset">
        <div v-if="!isEditMode">
            <LibraryBreadcrumb :current-id="dataset_id" :full_path="dataset.full_path" />
            <!-- top bar icons -->
            <button title="Download dataset" class="mr-1 mb-2" @click="download(datasetDownloadFormat, dataset_id)">
                <font-awesome-icon icon="download" /> Download
            </button>
            <button @click="importToHistory" title="Import dataset into history" class="mr-1 mb-2">
                <font-awesome-icon icon="book" />
                to History
            </button>
            <button
                @click="isEditMode = true"
                v-if="dataset.can_user_modify"
                title="Modify library item"
                class="mr-1 mb-2"
            >
                <font-awesome-icon icon="pencil-alt" />
                Modify
            </button>
            <b-button title="Attempt to detect the format of dataset" @click="detectDatatype" class="mr-1 mb-2">
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
        <b-table v-if="table_items" :fields="fields" :items="table_items" thead-class="d-none" striped small>
            <template v-slot:cell(value)="row">
                {{ debug(row.item) }}
                <div v-if="!isEditMode">
                    {{row.item.value}}
                </div>
                <div v-else>
                    <textarea></textarea>
                </div>
            </template>
        </b-table>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faUsers, faRedo, faPencilAlt, faBook, faDownload } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
import mod_import_dataset from "components/Libraries/LibraryFolder/TopToolbar/import-to-history/import-dataset";

import { Services } from "components/Libraries/LibraryFolder/services";
import LibraryBreadcrumb from "components/Libraries/LibraryFolder/LibraryBreadcrumb";
import download from "components/Libraries/LibraryFolder/TopToolbar/download";
import CopyToClipboard from "components/CopyToClipboard";
import { Toast } from "ui/toast";
import { fieldsTitles } from "./fields";

library.add(faUsers, faRedo, faBook, faDownload, faPencilAlt);

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
            isEditMode: false,
            fields: [
                {
                    key: "name",
                },
                { key: "value" },
            ],
        };
    },
    created() {
        this.services = new Services({ root: this.root });
        this.services.getDataset(this.dataset_id).then((response) => {
            this.dataset = response;
            this.table_items = buildFields(this.fieldTitles, this.dataset);

            console.log(this.table_items);
            console.log(this.dataset);
        });
    },
    methods: {
        detectDatatype() {
            const payload = { file_ext: "auto" };
            this.services.detectDatatype(
                this.dataset_id,
                payload,
                () => Toast.success("Changes to library dataset saved."),
                (error) => Toast.success(error)
            );
        },
        importToHistory() {
            new mod_import_dataset.ImportDatasetModal({
                selected: { dataset_ids: [this.dataset_id] },
            });
        },
        debug(e) {
            console.log(e);
        },
    },
};
</script>
