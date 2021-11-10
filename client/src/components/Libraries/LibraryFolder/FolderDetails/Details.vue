<template>
    <div>
        <b-button class="details-btn" title="Show location details" v-b-modal.details-modal>
            <font-awesome-icon icon="info-circle" /> Details
        </b-button>

        <b-modal id="details-modal" :title="titleLocationDetails" @show="getDetails" ok-only title-tag="h2">
            <div>
                <b-alert :show="hasError" variant="danger"> {{ error }} </b-alert>
                <div v-if="libraryDetails">
                    <h3>Library</h3>
                    <b-table-lite :items="libraryDetails" thead-class="d-none" />
                </div>
                <div>
                    <h3>Folder</h3>
                    <b-table-lite :items="folderDetails" thead-class="d-none" />
                </div>
            </div>
        </b-modal>
    </div>
</template>

<script>
import _l from "utils/localization";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

library.add(faInfoCircle);

function buildLibraryDetailsFields(data) {
    const libraryDetails = [
        { name: "Name", value: data.name },
        { name: "Description", value: data.description },
        { name: "Synopsis", value: data.synopsis },
        { name: "ID", value: data.id },
    ];
    if (data.create_time_pretty !== "") {
        libraryDetails.push({ name: "Created", value: data.create_time_pretty });
    }
    return libraryDetails;
}

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        metadata: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            titleLocationDetails: _l("Location Details"),
            libraryDetails: null,
            folderDetails: null,
            error: null,
        };
    },
    computed: {
        /** @return {Boolean} */
        hasError() {
            return this.error !== null;
        },
    },
    methods: {
        async getDetails() {
            try {
                const url = `${getAppRoot()}api/libraries/${this.metadata.parent_library_id}`;
                const response = await axios.get(url);

                this.libraryDetails = buildLibraryDetailsFields(response.data);
                this.folderDetails = [
                    { field: "Name", value: this.metadata.folder_name },
                    { field: "Description", value: this.metadata.folder_description },
                    { field: "ID", value: this.id },
                ];
                this.error = null;
            } catch (e) {
                this.libraryDetails = null;
                this.error = `Failed to retrieve library details. ${e}`;
            }
        },
    },
};
</script>
