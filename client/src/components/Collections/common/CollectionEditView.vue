<template>
    <div>
        <h4>{{ l("Edit Collection Attributes") }}</h4>
        <b-alert show variant="warning" dismissible>
            {{
                l(
                    "Collections are immutable. This means there will be some things you cannot change without creating a new collection. "
                )
            }}
        </b-alert>
        <div v-if="jobError">
            <b-alert show variant="danger" dismissible>
                {{ errorMessage }}
            </b-alert>
        </div>
        <b-tabs content-class="mt-3">
            <b-tab>
                <template v-slot:title> <i class="fa fa-bars"></i>{{ l(" Attributes") }}</template>
                <b>{{ l("Name: ") }}</b> <i>{{ collectionName }}</i>
                <br />
                <b>{{ l("Collection Type: ") }}</b> <i>{{ collectionType }}</i>
                <br />
                <b>{{ l("Elements: ") }}</b> <br />
                <div v-for="element in collectionElements" :key="element">{{ element.element_identifier }} <br /></div>
            </b-tab>
            <b-tab>
                <template v-slot:title> <i class="fa fa-table"></i>{{ l(" Database/Build") }}</template>
                <div class="alert alert-secondary" role="alert">
                    <div class="float-left">
                        Change database/genome of all elements in collection
                    </div>
                    <div class="text-right">
                        <button
                            class="save-collection btn btn-primary"
                            @click="clickedSave('dbkey', genome)"
                            :disabled="genome.id == databaseKeyFromElements"
                        >
                            {{ l("Save") }}
                        </button>
                    </div>
                </div>
                <b>{{ l("Database/Build: ") }}</b>
                <multiselect
                    v-model="genome"
                    deselect-label="Can't remove this value"
                    track-by="id"
                    label="text"
                    :options="genomes"
                    :searchable="true"
                    :allow-empty="false"
                >
                    {{ genome.text }}
                    <!-- <template slot="afterList">
                        <div v-observe-visibility="reachedEndOfList" v-if="hasMorePages">
                            <span class="spinner fa fa-spinner fa-spin fa-1x" />
                        </div>
                    </template> -->
                </multiselect>
                <i>original input: {{ databaseKeyFromElements }}</i>
            </b-tab>
            <b-tab>
                <template v-slot:title> <i class="fa fa-gear"></i>{{ l(" Convert") }}</template>
                <b>{{ l("Datatype: ") }}</b> <i>{{ datatypeFromElements }}</i>
            </b-tab>
            <b-tab>
                <template v-slot:title> <i class="fa fa-database"></i>{{ l(" Datatype") }}</template>
                <div class="alert alert-secondary" role="alert">
                    <div class="float-left">
                        Change datatype of all elements in collection
                    </div>
                    <div class="text-right">
                        <button
                            class="save-collection btn btn-primary"
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
                <template v-slot:title> <i class="fa fa-user"></i>{{ l(" Permissions") }}</template>
                <p>WIP Permissions</p>
            </b-tab>
        </b-tabs>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import axios from "axios";
import { prependPath } from "utils/redirect";
import { waitOnJob } from "components/JobStates/wait";
import UploadUtils from "mvc/upload/upload-utils";
import _l from "utils/localization";
import Multiselect from "vue-multiselect";
import { errorMessageAsString } from "utils/simple-error";
//import VueObserveVisibility from "vue-observe-visibility";

//Vue.use(VueObserveVisibility);
Vue.use(BootstrapVue);
export default {
    created() {
        this.apiCallToGetData();
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
    components: { Multiselect },
    data: function () {
        return {
            collection_data: {}, //all data from the response
            extensions: [],
            genomes: [],
            selectedGenome: {},
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
        genome: {
            get() {
                return this.selectedGenome;
            },
            set(element) {
                this.selectedGenome = element;
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
                    console.log("collection_data", this.collection_data);
                });

            //TODO error handling
        },
        getDatabaseKeyFromElements: function () {
            const dbkeysInCollection = [];
            for (var index in this.collectionElements) {
                var element = this.collectionElements[index];
                if (!dbkeysInCollection.includes(element.object.metadata_dbkey)) {
                    dbkeysInCollection.push(element.object.metadata_dbkey);
                }
            }
            console.log("dbkeysInCollection", dbkeysInCollection);
            if (dbkeysInCollection.length == 1) {
                this.databaseKeyFromElements = dbkeysInCollection[0];
            } else {
                this.databaseKeyFromElements = "?";
            }
            this.selectedGenome = this.genomes.find((element) => element.id == this.databaseKeyFromElements);
            console.log(this.selectedGenome, "in getDBfromE");
        },
        getExtensionFromElements: function () {
            const datatypesInCollection = [];
            for (var index in this.collectionElements) {
                var element = this.collectionElements[index];
                if (!datatypesInCollection.includes(element.object.file_ext)) {
                    datatypesInCollection.push(element.object.file_ext);
                }
            }
            if (datatypesInCollection.length == 1) {
                this.datatypeFromElements = datatypesInCollection[0];
            } else {
                this.datatypeFromElements = UploadUtils.DEFAULT_EXTENSION.id;
            }
            this.selectedExtension = this.extensions.find((element) => element.id == this.datatypeFromElements);
        },
        clickedSave: function (attribute, newValue) {
            console.log("clicked save");
            const url = prependPath("/api/dataset_collections/" + this.collection_id);
            const data = { attribute: attribute, newValue: newValue.id };
            axios
                .put(url, data)
                .then((response) => {
                    console.log("successssss");
                    this.apiCallToGetData();
                })
                .catch(this.handleError);
            // hit put /api/dataset_collections/this.collection_id
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
