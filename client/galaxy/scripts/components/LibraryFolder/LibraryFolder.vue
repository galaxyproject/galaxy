<template>
    <div>
        <div v-if="folderContents.length <= 0" class="d-flex justify-content-center m-5">
            <font-awesome-icon icon="spinner" spin size="9x"/>
        </div>
        <div v-else>
            <b-table
                    id="folder-table"
                    striped
                    hover
                    :fields="fields"
                    :items="folderContents"
                    :per-page="perPage"
                    :current-page="currentPage"
            >
                <b-thead>
                    <button>test</button>
                </b-thead>
                <template v-slot:cell(type_icon)="row">
                    <font-awesome-icon v-if="row.item.type === 'folder'" :icon="['far','folder']" title="Folder"/>
                    <font-awesome-icon v-else-if="row.item.type === 'file'" title="Dataset" :icon="['far','file']"/>
                </template>
                <template v-slot:cell(raw_size)="row">
                    <div v-if="row.item.type === 'file'" v-html="bytesToString(row.item.raw_size)"></div>
                </template>
                <template v-slot:cell(state)="row">
                    <div v-if="row.item.state != 'ok'">
                        {{ row.item.state }}
                    </div>
                </template>
                <template v-slot:cell(update_time)="row">
                    <UtcDate :date="row.item.update_time" mode="elapsed"/>
                </template>
                <template v-slot:cell(is_unrestricted)="row">
                    <font-awesome-icon v-if="row.item.is_unrestricted"
                                       title="Unrestricted dataset"
                                       icon="globe"/>

                    <font-awesome-icon v-else-if="row.item.is_private" title="Private dataset"
                                       icon="key"/>
                    <font-awesome-icon v-else title="Restricted dataset"
                                       icon="shield-alt"/>
                </template>

            </b-table>
            <b-container>

                <b-row class="justify-content-md-center">
                    <b-col md="auto">
                        <b-pagination
                                v-model="currentPage"
                                :total-rows="rows"
                                :per-page="perPage"
                                aria-controls="folder-table"
                        >

                        </b-pagination>
                    </b-col>
                    <b-col cols="1.5">
                        <table>
                            <tr>
                                <td class="m-0 p-0">
                                    <b-form-input
                                            class="pagination-input-field"
                                            id="paginationPerPage"
                                            autocomplete="off"
                                            type="number"
                                            v-model="perPage"
                                    />
                                </td>
                                <td class="text-muted ml-1 paginator-text">
                                    <span class="pagination-total-pages-text">per page, {{rows}} total</span>
                                </td>
                            </tr>
                        </table>
                    </b-col>
                </b-row>
            </b-container>


        </div>
    </div>
</template>

<script>
    import Vue from "vue";
    import {getAppRoot} from "onload/loadConfig";
    import {FontAwesomeIcon} from "@fortawesome/vue-fontawesome";
    import {library} from "@fortawesome/fontawesome-svg-core";
    import {faFile} from "@fortawesome/free-regular-svg-icons";
    import {faFolder} from "@fortawesome/free-regular-svg-icons";
    import {faSpinner} from "@fortawesome/free-solid-svg-icons";
    import {faShieldAlt} from "@fortawesome/free-solid-svg-icons";
    import {faGlobe} from "@fortawesome/free-solid-svg-icons";
    import {faKey} from "@fortawesome/free-solid-svg-icons";

    import UtcDate from "components/UtcDate";
    import BootstrapVue from "bootstrap-vue";
    import {Services} from "./services";
    import Utils from "utils/utils";

    library.add(faFile);
    library.add(faFolder);
    library.add(faSpinner);
    library.add(faShieldAlt);
    library.add(faKey);
    library.add(faGlobe);

    Vue.use(BootstrapVue);

    export default {
        props: {
            folder_id: {
                type: String,
                required: true,
            },
        },
        components: {
            UtcDate,
            FontAwesomeIcon
        },
        data() {
            return {
                error: null,
                currentPage: 1,
                fields: [
                    {
                        label: "",
                        key: "type_icon",
                    },
                    {
                        label: "Name",
                        key: "name",
                        sortable: true,
                    },
                    {
                        label: "Description",
                        key: "message",
                        sortable: false,
                    },
                    {
                        label: "Data Type",
                        key: "type",
                        sortable: true,
                    },
                    {
                        label: "Size",
                        key: "raw_size",
                        sortable: true,
                    },
                    {
                        label: "State",
                        key: "state",
                        sortable: true,
                    },
                    {
                        label: "Date Updated (UTC)",
                        key: "update_time",
                        sortable: true,
                    },
                    {
                        label: "",
                        key: "is_unrestricted",
                        sortable: false,
                    },
                ],
                folderContents: [],
                perPage: 2
            };
        },
        computed: {
            rows() {
                return this.folderContents.length
            }
        },
        created() {
            this.root = getAppRoot();
            this.services = new Services({root: this.root});
            this.services
                .getFolderContents(this.folder_id)
                .then((response) => {
                    response.folder_contents.forEach(content => content.update_time = new Date(content.update_time).toISOString())
                    this.folderContents = response.folder_contents;
                    console.log(this.folderContents)
                })
                .catch((error) => {
                    this.error = error;
                });
        },
        methods: {
            bytesToString(raw_size) {
                return Utils.bytesToString(raw_size)
            }
        }

    };
</script>

<style scoped>
    .pagination-input-field {
        max-width: 60px
    }

    .pagination-total-pages-text {
        margin-left: .25rem;
    }
</style>

