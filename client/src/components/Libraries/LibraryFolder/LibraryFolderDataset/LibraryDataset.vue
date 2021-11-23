<template>
    <div v-if="dataset">
        <div v-if="!isEditMode">
            <LibraryBreadcrumb :current-id="dataset_id" :full_path="dataset.full_path" />
            <!-- Toolbar -->
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
                    name: 'LibraryFolderDatasetPermissions',
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
        <!-- Table -->
        <b-table
            v-if="table_items"
            :fields="fields"
            :items="table_items"
            class="mt-2"
            thead-class="d-none"
            striped
            small
        >
            <template v-slot:cell(name)="row">
                <strong>{{ row.item.name }}</strong>
            </template>
            <template v-slot:cell(value)="row">
                <div v-if="isEditMode">
                    <b-form-input
                        v-if="row.item.name === fieldTitles.name"
                        :value="row.item.value"
                        v-model="modifiedDataset.name"
                    />
                    <multiselect
                        v-else-if="row.item.name === fieldTitles.file_ext"
                        v-model="modifiedDataset.file_ext"
                        deselect-label="Can't remove this value"
                        :options="availableDatatypes"
                        :searchable="true"
                        :allow-empty="false"
                    />
                    <multiselect
                        v-else-if="row.item.name === fieldTitles.genome_build"
                        v-model="selectedGenome"
                        deselect-label="Can't remove this value"
                        track-by="id"
                        label="text"
                        :options="availableGenomes"
                        :searchable="true"
                        :allow-empty="false"
                    />
                    <b-form-input
                        v-else-if="row.item.name === fieldTitles.message"
                        :value="row.item.value"
                        v-model="modifiedDataset.message"
                    />
                    <b-form-input
                        v-else-if="row.item.name === fieldTitles.misc_info"
                        :value="row.item.value"
                        v-model="modifiedDataset.misc_info"
                    />
                    <div v-else>{{ row.item.value }}</div>
                </div>
                <div v-else>
                    <div>{{ row.item.value }}</div>
                </div>
            </template>
        </b-table>
        <!-- Edit Controls -->
        <div v-if="isEditMode">
            <b-button @click="isEditMode = false" class="mr-1 mb-2">
                <font-awesome-icon :icon="['fas', 'times']" />
                Cancel
            </b-button>
            <b-button @click="updateDataset" class="mr-1 mb-2">
                <font-awesome-icon :icon="['far', 'save']" />
                Save
            </b-button>
        </div>
        <!-- Peek View -->
        <div v-if="dataset.peek" v-html="dataset.peek" />
    </div>
</template>

<script>
import Multiselect from "vue-multiselect";
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
import { fieldTitles } from "components/Libraries/LibraryFolder/LibraryFolderDataset/constants";

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
        Multiselect,
    },
    data() {
        return {
            fieldTitles: fieldTitles,
            dataset: undefined,
            currentRouteName: window.location.href,
            datasetDownloadFormat: "uncompressed",
            download: download,
            table_items: [],
            availableDatatypes: [],
            availableGenomes: [],
            selectedGenome: {},
            modifiedDataset: {},
            isEditMode: false,
            fields: [{ key: "name" }, { key: "value" }],
        };
    },
    async created() {
        this.services = new Services({ root: this.root });
        const datasetResponse = await this.services.getDataset(this.dataset_id);
        this.populateDatasetDetailsTable(datasetResponse);
        //TODO use providers
        this.availableDatatypes = await this.services.getDatatypes();
        this.availableDatatypes.unshift("auto");
        this.availableGenomes = await this.services.getGenomes();
        this.selectedGenome = this.availableGenomes.find((genome) => genome.id == this.dataset.genome_build);
    },
    methods: {
        populateDatasetDetailsTable(data) {
            this.dataset = data;
            Object.assign(this.modifiedDataset, this.dataset);
            this.table_items = buildFields(this.fieldTitles, this.dataset);
        },
        detectDatatype() {
            this.services.updateDataset(
                this.dataset_id,
                { file_ext: "auto" },
                (response) => {
                    this.populateDatasetDetailsTable(response);
                    Toast.success("Changes to library dataset saved.");
                },
                (error) => Toast.error(error)
            );
        },
        updateDataset() {
            if (this.selectedGenome.id !== this.dataset.genome_build) {
                this.modifiedDataset.genome_build = this.selectedGenome.id;
            }
            //TODO send only diff?
            this.services.updateDataset(
                this.dataset_id,
                this.modifiedDataset,
                (response) => {
                    this.populateDatasetDetailsTable(response);
                    Toast.success("Changes to library dataset saved.");
                },
                (error) => Toast.error(error)
            );
            this.isEditMode = false;
        },
        importToHistory() {
            new mod_import_dataset.ImportDatasetModal({
                selected: { dataset_ids: [this.dataset_id] },
            });
        },
    },
};
</script>
