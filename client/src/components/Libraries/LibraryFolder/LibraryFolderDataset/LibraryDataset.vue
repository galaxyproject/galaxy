<template>
    <div v-if="dataset">
        <LibraryBreadcrumb :current-id="dataset_id" :full_path="dataset.full_path" />
        <!-- top bar icons -->
        <button title="Download dataset" class="mr-1 mb-2" @click="download(datasetDownloadFormat, dataset_id)">
            <font-awesome-icon icon="download" /> Download
        </button>
        <button title="Import dataset into history" class="mr-1 mb-2">
            <font-awesome-icon icon="book" />
            to History
        </button>
        <button v-if="dataset.can_user_modify" title="Modify library item" class="mr-1 mb-2">
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
            :to="{ name: `LibraryFolderDatasetPermissions`, params: { folder_id: folder_id, dataset_id: dataset_id } }"
        >
            <font-awesome-icon icon="users" />
            Permissions
        </b-button>

        <div v-if="dataset.is_unrestricted">
            This dataset is unrestricted so everybody with the link can access it.
            <copy-to-clipboard
                message="A link to current dataset was copied to your clipboard"
                :text="currentRouteName"
                title="Copy link to this dataset "
            />
        </div>
        <b-table> </b-table>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faUsers, faRedo, faPencilAlt, faBook, faDownload } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";

import { Services } from "components/Libraries/LibraryFolder/services";
import LibraryBreadcrumb from "components/Libraries/LibraryFolder/LibraryBreadcrumb";
import download from "components/Libraries/LibraryFolder/TopToolbar/download";
import CopyToClipboard from "components/CopyToClipboard";
import { Toast } from "ui/toast";

library.add(faUsers, faRedo, faBook, faDownload, faPencilAlt);
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
            dataset: undefined,
            currentRouteName: window.location.href,
            datasetDownloadFormat: "uncompressed",
            download: download,
        };
    },
    created() {
        this.services = new Services({ root: this.root });
        this.services.getDataset(this.dataset_id).then((response) => {
            this.dataset = response;
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
    },
};
</script>
