<template>
    <div v-if="dataset">
        <button
            data-toggle="tooltip"
            data-placement="top"
            title="Attempt to detect the format of dataset"
            class="btn btn-secondary toolbtn_detect_datatype toolbar-item mr-1"
            type="button"
        >
            <span class="fa fa-redo"></span>
           Auto-detect datatype
        </button>
        <button
            title="Manage permissions"
            v-if="dataset.can_user_manage"
            :to="{ name: `LibraryFolderDatasetPermissions`, params: { folder_id: folder_id, dataset_id: dataset_id } }"
        >
            <font-awesome-icon icon="users" />
            Permissions
        </button>
        <LibraryBreadcrumb :current-id="dataset_id" :full_path="dataset.full_path" />

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
import { faUsers } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";

import { Services } from "components/Libraries/LibraryFolder/services";
import LibraryBreadcrumb from "components/Libraries/LibraryFolder/LibraryBreadcrumb";
import CopyToClipboard from "components/CopyToClipboard";
library.add(faUsers);
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
        };
    },
    created() {
        this.services = new Services({ root: this.root });
        this.services.getDataset(this.dataset_id).then((response) => {
            this.dataset = response;
        });
        console.log(this.$router.currentRoute.path); // path is /post
    },
};
</script>
