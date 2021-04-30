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
                <template v-slot:title> <font-awesome-icon icon="table" /> &nbsp; {{ l("Database/Build") }}</template>
                <database-edit-tab
                    :databaseKeyFromElements="databaseKeyFromElements"
                    :genomes="genomes"
                    @clicked-save="clickedSave"
                />
            </b-tab>
            <b-tab v-if="atleastOneSuitableConverter">
                <template v-slot:title> <font-awesome-icon icon="cog" /> &nbsp; {{ l("Convert") }}</template>
                <div class="alert alert-secondary" role="alert">
                    <div class="float-left">Convert all datasets to new format</div>
                    <div class="text-right">
                        <button
                            class="run-tool-collection-edit btn btn-primary"
                            @click="clickedConvert"
                            :disabled="chosenConverter == {}"
                        >
                            {{ l("Convert Collection") }}
                        </button>
                    </div>
                </div>
                <b>{{ l("Convterter Tool: ") }}</b>
                <multiselect
                    v-model="chosenConverter"
                    deselect-label="Can't remove this value"
                    track-by="name"
                    label="name"
                    :options="suitableConverters"
                    :searchable="true"
                    :allow-empty="true"
                >
                </multiselect>
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
                </multiselect>
            </b-tab>
        </b-tabs>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import axios from "axios";
import { prependPath } from "utils/redirect";
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
import store from "../../../store/index";

library.add(faDatabase);
library.add(faTable);
library.add(faBars);
library.add(faCog);
library.add(faUser);

Vue.use(BootstrapVue);
export default {
    created() {
        this.getDatatypesAndGenomes();
        this.getCollectionDataAndAttributes();
        this.getConverterList();
    },
    components: { Multiselect, DatabaseEditTab, FontAwesomeIcon },
    data: function () {
        return {
            attributes_data: {},
            extensions: [],
            genomes: [],
            selectedExtension: {},
            chosenConverter: {},
            databaseKeyFromElements: null,
            suitableConverters: [],
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
        extension: {
            get() {
                return this.selectedExtension;
            },
            set(element) {
                this.selectedExtension = element;
            },
        },
        atleastOneSuitableConverter: function () {
            return this.suitableConverters.length > 0;
        },
    },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
        getDatatypesAndGenomes: async function () {
            let datatypes = store.getters.getUploadDatatypes();
            if (!datatypes || datatypes.length == 0) {
                await store.dispatch("fetchUploadDatatypes");
                datatypes = store.getters.getUploadDatatypes();
            }
            this.extensions = datatypes;
            let genomes = store.getters.getUploadGenomes();
            if (!genomes || genomes.length == 0) {
                await store.dispatch("fetchUploadGenomes");
                genomes = store.getters.getUploadGenomes();
            }
            this.genomes = genomes;
        },
        getCollectionDataAndAttributes: async function () {
            let attributesGet = store.getters.getCollectionAttributes(this.collection_id);
            if (attributesGet == null) {
                await store.dispatch("fetchCollectionAttributes", this.collection_id);
                attributesGet = store.getters.getCollectionAttributes(this.collection_id);
            }
            this.attributes_data = attributesGet;
            this.getDatabaseKeyFromElements();
            this.getExtensionFromElements();
        },
        getDatabaseKeyFromElements: function () {
            this.databaseKeyFromElements = this.attributes_data.dbkey;
        },
        getExtensionFromElements: function () {
            this.datatypeFromElements = this.attributes_data.extension;
            this.selectedExtension = this.extensions.find((element) => element.id == this.datatypeFromElements);
        },
        getConverterList: async function () {
            axios.get(prependPath("/api/datatypes/suitable_converters/" + this.collection_id)).then((response) => {
                this.suitableConverters = response.data;
            });
        },
        clickedSave: function (attribute, newValue) {
            const url = prependPath("/api/dataset_collections/" + this.collection_id);
            const data = {};
            if (attribute == "dbkey") {
                data["dbkey"] = newValue.id;
            } else if (attribute == "file_ext") {
                data["file_ext"] = newValue.id;
            }
            axios
                .put(url, data)
                .then((response) => {
                    this.apiCallToGetData();
                    this.getDatabaseKeyFromElements();
                    this.getExtensionFromElements();
                })
                .catch(this.handleError);
        },
        clickedConvert: function () {
            console.log("this.chosenConverter = ", this.chosenConverter);
            const url = prependPath("/api/tools/");
            const data = {
                tool_id: this.chosenConverter.tool_id,
                inputs: { input: { batch: true, values: [{ src: "hdca", id: this.collection_id }] } },
            };
            axios
                .post(url, data)
                .then((response) => {
                    console.log("donee!");
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
