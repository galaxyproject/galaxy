<template>
    <div>
        <h4>{{ l("Edit Collection Attributes") }}</h4>
        <b-alert show variant="info" dismissible>
            {{ l("This will create a new collection in your History. Your quota usage will not increase. ") }}
        </b-alert>
        <div v-if="jobError">
            <b-alert show variant="danger" dismissible>
                {{ errorMessage }}
            </b-alert>
        </div>
        <b-tabs content-class="mt-3">
            <b-tab>
                <template v-slot:title> <font-awesome-icon icon="bars" /> &nbsp; {{ l("Attributes") }}</template>
                <b>{{ l("Name: ") }}</b> <i>{{ collectionName }}</i>
                <br />
                <b>{{ l("Collection Type: ") }}</b> <i>{{ collectionType }}</i>
                <br />
                <b>{{ l("Elements: ") }}</b> <br />
                <div v-for="element in collectionElements" :key="element">{{ element.element_identifier }} <br /></div>
            </b-tab>
            <b-tab>
                <template v-slot:title>
                    <font-awesome-icon icon="table" /> &nbsp; {{ l("Database/Build") }}</template
                >
                <database-edit-tab :databaseKeyFromElements="databaseKeyFromElements" :genomes="genomes" />
            </b-tab>
            <b-tab>
                <template v-slot:title> <font-awesome-icon icon="cog" /> &nbsp; {{ l("Convert") }}</template>
                <b>{{ l("Datatype: ") }}</b> <i>{{ datatypeFromElements }}</i>
            </b-tab>
            <b-tab>
                <template v-slot:title> <font-awesome-icon icon="database" /> &nbsp; {{ l("Datatype") }}</template>
                <div class="alert alert-secondary" role="alert">
                    <div class="float-left">Change datatype of all elements in collection</div>
                    <div class="text-right">
                        <button
                            class="save-collection-edit btn btn-primary"
                            @click="clickedSave('file_ext', extension)"
                            :disabled="extension.id == datatypeFromElements"
                        >
                            {{ l("Save") }}
                        </button>
                    </div>
                </div>
                <b>{{ l("Datatype: ") }}</b>
                <multiselect
                    v-model="extension"
                    deselect-label="Can't remove this value"
                    track-by="id"
                    label="text"
                    :options="extensions"
                    :searchable="true"
                    :allow-empty="false"
                >
                    {{ extension.text }}
                    <!-- <template slot="afterList">
                        <div v-observe-visibility="reachedEndOfList" v-if="hasMorePages">
                            <span class="spinner fa fa-spinner fa-spin fa-1x" />
                        </div>
                    </template> --> </multiselect
                ><i>original input: {{ datatypeFromElements }}</i>
            </b-tab>
            <b-tab>
                <template v-slot:title> <font-awesome-icon icon="user" /> &nbsp;{{ l("Permissions") }}</template>
                <p>WIP Permissions</p>
            </b-tab>
        </b-tabs>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import axios from "axios";
import { prependPath } from "utils/redirect";
import UploadUtils from "mvc/upload/upload-utils";
import _l from "utils/localization";
import Multiselect from "vue-multiselect";
import { errorMessageAsString } from "utils/simple-error";
import DatabaseEditTab from "./DatabaseEditTab";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faDatabase } from "@fortawesome/free-solid-svg-icons";
import { faTable } from "@fortawesome/free-solid-svg-icons";
import { faBars } from "@fortawesome/free-solid-svg-icons";
import { faUser } from "@fortawesome/free-solid-svg-icons";
import { faCog } from "@fortawesome/free-solid-svg-icons";

//import VueObserveVisibility from "vue-observe-visibility";

//Vue.use(VueObserveVisibility);
library.add(faDatabase);
library.add(faTable);
library.add(faBars);
library.add(faCog);
library.add(faUser);

Vue.use(BootstrapVue);
export default {
    created() {
        this.apiCallToGetData();
        this.apiCallToGetAttributes();
        UploadUtils.getUploadDatatypes(true, UploadUtils.AUTO_EXTENSION)
            .then((extensions) => {
                this.extensions = extensions;
            })
            .catch((err) => {
                console.log("Error in CollectionEditor, unable to load datatypes", err);
            });
        UploadUtils.getUploadGenomes(UploadUtils.DEFAULT_GENOME)
            .then((genomes) => {
                this.genomes = genomes;
            })
            .catch((err) => {
                console.log("Error in CollectionEditor, unable to load genomes", err);
            });
    },
    components: { Multiselect, DatabaseEditTab, FontAwesomeIcon },
    data: function () {
        return {
            collection_data: {}, //all data from the response
            attributes_data: {},
            extensions: [],
            genomes: [],
            selectedExtension: {},
            databaseKeyFromElements: null,
            datatypeFromElements: null,
            errorMessage: null,
            jobError: null,
        };
    },
    props: {
        collection_id: {
            type: String,
            required: true,
        },
    },
    computed: {
        collectionName: {
            get() {
                return this.collection_data.name;
            },
            //TODO : #6966
            // set(collection_name) {
            //     this.collection_data.name = collection_name;
            // },
        },
        collectionType: {
            get() {
                return this.collection_data.collection_type;
            },
        },
        collectionElements: {
            get() {
                return this.collection_data.elements;
            },
        },
        numberOfCollectionElements: {
            get() {
                return this.collection_data.element_count;
            },
        },
        extension: {
            get() {
                return this.selectedExtension;
            },
            set(element) {
                this.selectedExtension = element;
            },
        },
    },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
        apiCallToGetData: function () {
            axios
                .get(prependPath("/api/dataset_collections/" + this.collection_id + "?instance_type=history"))
                .then((response) => {
                    this.collection_data = response.data;
                    this.getDatabaseKeyFromElements();
                    this.getExtensionFromElements();
                });

            //TODO error handling
        },
        apiCallToGetAttributes: function () {
            axios
                .get(prependPath("/api/dataset_collections/" + this.collection_id + "/attributes"))
                .then((response) => {
                    this.attributes_data = response.data;
                    this.getDatabaseKeyFromElements();
                    this.getExtensionFromElements();
                });
            //TODO error handling
        },
        getDatabaseKeyFromElements: function () {
            this.databaseKeyFromElements = this.attributes_data.dbkey;
            // this.selectedGenome = this.genomes.find((element) => element.id == this.databaseKeyFromElements);
        },
        getExtensionFromElements: function () {
            this.datatypeFromElements = this.attributes_data.extension;
            this.selectedExtension = this.extensions.find((element) => element.id == this.datatypeFromElements);
        },
        clickedSave: function (attribute, newValue) {
            const url = prependPath("/api/dataset_collections/" + this.collection_id);
            const data = {};
            if (attribute == "dbkey") {
                data.add({ dbkey: newValue.id });
            } else if (attribute == "file_ext") {
                data.add({ file_ext: newValue.id });
            }

            axios
                .put(url, data)
                .then((response) => {
                    this.apiCallToGetData();
                })
                .catch(this.handleError);
        },
        handleError: function (err) {
            this.errorMessage = errorMessageAsString(err, "History import failed.");
            if (err?.data?.stderr) {
                this.jobError = err.data;
            }
        },
    },
};
</script>

<style scoped></style>
