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

function buildFields(fields, data) {
    return Object.entries(fields).flatMap(([property, title]) =>
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
            folderFields: { folder_name: _l("Name"), folder_description: _l("Description"), id: "ID" },
            libraryFields: {
                name: _l("Name"),
                description: _l("Description"),
                synopsis: _l("Synopsis"),
                create_time_pretty: _l("Created"),
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
                this.error = `${_l("Failed to retrieve library details.")} ${e}`;
            }
        },
    },
};
</script>
