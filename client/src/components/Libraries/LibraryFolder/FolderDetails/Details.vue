<template>
    <div>
        <b-button
            class="details-btn"
            title="Show location details"
            v-b-modal.details-modal
            data-testid="loc-details-btn"
        >
            <font-awesome-icon icon="info-circle" /> Details
        </b-button>

        <b-modal id="details-modal" :title="titleLocationDetails" @show="getDetails" ok-only title-tag="h3">
            <div>
                <b-alert :show="hasError" variant="danger"> {{ error }} </b-alert>
                <div v-if="libraryDetails">
                    <b-table-lite
                        :items="libraryDetails"
                        :fields="getFieldsWithHeaderTitle('Library')"
                        striped
                        small
                        data-testid="library-table"
                    />
                </div>
                <div>
                    <b-table-lite
                        :items="folderDetails"
                        :fields="getFieldsWithHeaderTitle('Folder')"
                        striped
                        small
                        data-testid="folder-table"
                    />
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
            fields: [
                { label: "Library", key: "name" },
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
                    { name: "Name", value: this.metadata.folder_name },
                    { name: "Description", value: this.metadata.folder_description },
                    { name: "ID", value: this.id },
                ];
                this.error = null;
            } catch (e) {
                this.libraryDetails = null;
                this.error = `Failed to retrieve library details. ${e}`;
            }
        },
        /** Create table fields to display just the first column
         * header as the table title.
         */
        getFieldsWithHeaderTitle(title) {
            return [
                { label: title, key: "name" },
                { label: "", key: "value" },
            ];
        },
    },
};
</script>
