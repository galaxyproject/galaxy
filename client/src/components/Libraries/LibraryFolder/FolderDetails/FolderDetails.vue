<template>
    <div>
        <b-button
            class="details-btn"
            title="Show location details"
            v-b-modal.details-modal
            data-testid="loc-details-btn"
        >
            <font-awesome-icon icon="info-circle" /> {{ detailsCaption }}
        </b-button>

        <b-modal
            id="details-modal"
            :static="isStatic"
            :title="titleLocationDetails"
            @show="getDetails"
            title-tag="h3"
            ok-only
        >
            <div>
                <b-alert :show="hasError" variant="danger" data-testid="error-alert"> {{ error }} </b-alert>
                <div v-if="libraryDetails">
                    <b-table-lite
                        :fields="fields"
                        :items="libraryDetails"
                        striped
                        small
                        caption-top
                        thead-class="d-none"
                        data-testid="library-table"
                    >
                        <template v-slot:table-caption>
                            <h4>
                                <b>{{ libraryHeader }}</b>
                            </h4>
                        </template>
                    </b-table-lite>
                </div>
                <div>
                    <b-table-lite
                        :fields="fields"
                        :items="folderDetails"
                        striped
                        small
                        caption-top
                        thead-class="d-none"
                        data-testid="folder-table"
                    >
                        <template v-slot:table-caption>
                            <h4>
                                <b>{{ folderHeader }}</b>
                            </h4>
                        </template>
                    </b-table-lite>
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

/** Maps the title in `fieldTitles` to the value of that property from the object `data`.
 * @param {Object} fieldTitles   Contains property/title pairs.
 * @param {Object} data     Contains property/value pairs.
 * @returns An array with name/value pairs with the corresponding title and the actual value
 * of the property contained in `data`.
 */
function buildFields(fieldTitles, data) {
    return Object.entries(fieldTitles).flatMap(([property, title]) =>
        data[property] ? { name: title, value: data[property] } : []
    );
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
        isStatic: {
            type: Boolean,
            required: false,
            default: false,
        },
    },
    data() {
        return {
            detailsCaption: _l("Details"),
            folderHeader: _l("Folder"),
            libraryHeader: _l("Library"),
            titleLocationDetails: _l("Location Details"),
            fields: [
                {
                    key: "name",
                    tdClass: "name-column",
                },
                { key: "value" },
            ],
            folderFieldTitles: { folder_name: _l("Name"), folder_description: _l("Description"), id: "ID" },
            libraryFieldTitles: {
                name: _l("Name"),
                description: _l("Description"),
                synopsis: _l("Synopsis"),
                create_time_pretty: _l("Created"),
                id: "ID",
            },
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
            // Compose the folder metadata with it's id as a new object
            const folderData = { ...this.metadata, ...{ id: this.id } };
            this.folderDetails = buildFields(this.folderFieldTitles, folderData);
            this.libraryDetails = await this.retrieveLibraryDetails();
        },
        async retrieveLibraryDetails() {
            try {
                this.error = null;
                const url = `${getAppRoot()}api/libraries/${this.metadata.parent_library_id}`;
                const response = await axios.get(url);
                return buildFields(this.libraryFieldTitles, response.data);
            } catch (e) {
                this.error = `${_l("Failed to retrieve library details.")} ${e}`;
                return null;
            }
        },
    },
};
</script>
<style>
/* Cannot be scoped because name-column is used in tdClass */
.name-column {
    width: 25%;
}
</style>
