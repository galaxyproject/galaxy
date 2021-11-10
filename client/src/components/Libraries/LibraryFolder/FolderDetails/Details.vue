<template>
    <div>
        <b-button class="details-btn" title="Show location details" v-b-modal.details-modal>
            <font-awesome-icon icon="info-circle" /> Details
        </b-button>

        <b-modal id="details-modal" :title="titleLocationDetails" @show="getDetails" ok-only title-tag="h3">
            <div>
                <b-alert :show="hasError" variant="danger"> {{ error }} </b-alert>
                <div v-if="libraryDetails">
                    <b-table-lite :items="libraryDetails" :fields="getFields('Library')" striped small />
                </div>
                <div>
                    <b-table-lite :items="folderDetails" :fields="getFields('Folder')" striped small />
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
        { key: "Name", value: data.name },
        { key: "Description", value: data.description },
        { key: "Synopsis", value: data.synopsis },
        { key: "ID", value: data.id },
    ];
    if (data.create_time_pretty !== "") {
        libraryDetails.push({ key: "Created", value: data.create_time_pretty });
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
            fields: [
                { label: "Library", key: "key" },
                { label: "", key: "value" },
            ],
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
                    { key: "Name", value: this.metadata.folder_name },
                    { key: "Description", value: this.metadata.folder_description },
                    { key: "ID", value: this.id },
                ];
                this.error = null;
            } catch (e) {
                this.libraryDetails = null;
                this.error = `Failed to retrieve library details. ${e}`;
            }
        },
        getFields(title) {
            return [
                { label: title, key: "key" },
                { label: "", key: "value" },
            ];
        },
    },
};
</script>
