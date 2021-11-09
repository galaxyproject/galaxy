<template>
    <div>
        <b-button title="Show location details" v-b-modal.details-modal>
            <font-awesome-icon icon="info-circle" /> Details
        </b-button>

        <b-modal id="details-modal" title="Location Details" @show="getDetails">
            <div>
                <table v-if="libraryDetails" class="grid table table-sm">
                    <thead>
                        <th style="width: 25%">Library</th>
                        <th></th>
                    </thead>
                    <tbody>
                        <tr>
                            <td>name</td>
                            <td>{{ libraryDetails.name }}</td>
                        </tr>
                        <tr v-if="libraryDetails.description">
                            <td>description</td>
                            <td>{{ libraryDetails.description }}</td>
                        </tr>
                        <tr v-if="libraryDetails.synopsis">
                            <td>synopsis</td>
                            <td>{{ libraryDetails.synopsis }}</td>
                        </tr>
                        <tr v-if="libraryDetails.create_time_pretty !== ''">
                            <td>created</td>
                            <td>
                                <span :title="libraryDetails.create_time">
                                    {{ libraryDetails.create_time_pretty }}
                                </span>
                            </td>
                        </tr>
                        <tr>
                            <td>id</td>
                            <td>{{ libraryDetails.id }}</td>
                        </tr>
                    </tbody>
                </table>
                <table class="grid table table-sm">
                    <thead>
                        <th style="width: 25%">Folder</th>
                        <th></th>
                    </thead>
                    <tbody>
                        <tr>
                            <td>name</td>
                            <td>{{ metadata.folder_name }}</td>
                        </tr>

                        <tr v-if="metadata.folder_description">
                            <td>description</td>
                            <td>{{ metadata.folder_description }}</td>
                        </tr>

                        <tr>
                            <td>id</td>
                            <td>{{ id }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </b-modal>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

library.add(faInfoCircle);

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
            libraryDetails: null,
            error: null,
        };
    },
    methods: {
        async getDetails() {
            try {
                const url = `${getAppRoot()}api/libraries/${this.metadata.parent_library_id}`;
                const response = await axios.get(url);
                this.libraryDetails = response.data;
            } catch (e) {
                this.error = `Failed to retrieve details. ${e}`;
            }
        },
    },
};
</script>
