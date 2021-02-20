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
        <b-tabs content-class="mt-3">
            <b-tab>
                <template v-slot:title> <i class="fa fa-bars"></i>{{ l(" Attributes") }}</template>
                <b>{{ l("Name: ") }}</b> <i>{{ collectionName }}</i
                ><br />
                <b>{{ l("Collection Type: ") }}</b> <i>{{ collectionType }}</i
                ><br />
                <b>{{ l("Elements: ") }}</b> <br />
                <div v-for="element in collectionElements" :key="element">{{ element.element_identifier }} <br /></div>
            </b-tab>
            <b-tab>
                <template v-slot:title> <i class="fa fa-table"></i>{{ l(" Database/Build") }}</template>
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
                <i>{{ databaseKeyFromElements }}</i>
            </b-tab>
            <b-tab>
                <template v-slot:title> <i class="fa fa-gear"></i>{{ l(" Convert") }}</template>
                <b>{{ l("Datatype: ") }}</b> <i>{{ datatypesFromElements }}</i>
            </b-tab>
            <b-tab>
                <template v-slot:title> <i class="fa fa-database"></i>{{ l(" Datatype") }}</template>
                <b>{{ l("Datatype: ") }}</b> <i>{{ datatypesFromElements }}</i>
            </b-tab>
            <b-tab>
                <template v-slot:title> <i class="fa fa-user"></i>{{ l(" Permissions") }}</template>
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
//import VueObserveVisibility from "vue-observe-visibility";

//Vue.use(VueObserveVisibility);
Vue.use(BootstrapVue);
export default {
    created() {
        this.apiCallToGetData();
        UploadUtils.getUploadDatatypes(true, UploadUtils.AUTO_EXTENSION)
            .then((extensions) => {
                this.extensions = extensions;
                //this.extension = UploadUtils.DEFAULT_EXTENSION;
            })
            .catch((err) => {
                console.log("Error in CollectionEditor, unable to load datatypes", err);
            });
        UploadUtils.getUploadGenomes(UploadUtils.DEFAULT_GENOME)
            .then((genomes) => {
                this.genomes = genomes;
                //this.genome = UploadUtils.DEFAULT_GENOME;
            })
            .catch((err) => {
                console.log("Error in CollectionEditor, unable to load genomes", err);
            });
    //     UploadUtils.getUploadDatatypes(
    //         (extensions) => {
    //             this.extensions = extensions;
    //             //this.extension = UploadUtils.DEFAULT_EXTENSION;
    //         },
    //         true,
    //         UploadUtils.AUTO_EXTENSION
    //     );
    //     UploadUtils.getUploadGenomes((genomes) => {
    //         this.genomes = genomes;
    //         //this.genome = UploadUtils.DEFAULT_GENOME;
    //     }, UploadUtils.DEFAULT_GENOME);
    },
    components: { Multiselect },
    data: function () {
        return {
            collection_data: {}, //all data from the response
            extensions: {},
            genomes: [],
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
        databaseKeyFromElements: {
            get() {
                const dbkeysInCollection = [];
                for (var index in this.collectionElements) {
                    var element = this.collectionElements[index];
                    if (!dbkeysInCollection.includes(element.object.metadata_dbkey)) {
                        dbkeysInCollection.push(element.object.metadata_dbkey);
                    }
                }
                if (dbkeysInCollection.length == 1) {
                    return dbkeysInCollection[0];
                } else {
                    return "?";
                }
            },
        },
        genome: {
            get() {
                return this.databaseKeyFromElements;
            },
        },
        datatypesFromElements: {
            get() {
                const datatypesInCollection = [];
                for (var index in this.collectionElements) {
                    var element = this.collectionElements[index];
                    if (!datatypesInCollection.includes(element.object.data_type)) {
                        datatypesInCollection.push(element.object.data_type);
                    }
                }
                if (datatypesInCollection.length == 1) {
                    return datatypesInCollection[0];
                } else {
                    return "?";
                }
            },
        },
        extension: {
            get() {
                return this.datatypesFromElements;
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
                    console.log("collection_data", this.collection_data);
                });

            //TODO error handling
        },
    },
};
</script>

<style scoped></style>
