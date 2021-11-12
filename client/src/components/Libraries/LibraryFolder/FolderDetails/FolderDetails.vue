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

        <b-modal
            id="details-modal"
            :static="isStatic"
            :title="titleLocationDetails"
            @show="getDetails"
            ok-only
            title-tag="h3"
        >
            <div>
                <b-alert :show="hasError" variant="danger" data-testid="error-alert"> {{ error }} </b-alert>
                <div v-if="libraryDetails">
                    <b-table-lite
                        :items="libraryDetails"
                        :fields="getFieldsWithHeaderTitle(libraryHeader)"
                        striped
                        small
                        data-testid="library-table"
                    />
                </div>
                <div>
                    <b-table-lite
                        :items="folderDetails"
                        :fields="getFieldsWithHeaderTitle(folderHeader)"
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

function buildFields(fields, data) {
    return Object.entries(fields).flatMap(([property, title]) =>
        data[property] ? { name: title, value: data[property] } : []
    );
}

export default {
    name: "FolderDetails",
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
        isStatic: {
            type: Boolean,
            required: false,
            default: false,
        },
    },
    data() {
        return {
            folderHeader: "Folder",
            libraryHeader: "Library",
            folderFields: { folder_name: "Name", folder_description: "Description", id: "ID" },
            libraryFields: {
                name: "Name",
                description: "Description",
                synopsis: "Synopsis",
                create_time_pretty: "Created",
                id: "ID",
            },
            titleLocationDetails: _l("Location Details"),
            libraryDetails: null,
            folderDetails: null,
            error: null,
        };
    },
    computed: {
        /** @return {Boolean} */
        hasError() {
            return !!this.error;
        },
    },
    methods: {
        async getDetails() {
            try {
                const url = `${getAppRoot()}api/libraries/${this.metadata.parent_library_id}`;
                const response = await axios.get(url);
                this.libraryDetails = buildFields(this.libraryFields, response.data);
                this.folderDetails = buildFields(this.folderFields, { ...this.metadata, ...{ id: this.id } });
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