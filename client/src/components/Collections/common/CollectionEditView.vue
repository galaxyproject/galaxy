<template>
    <div>
        <h4>{{ l("Edit Collection Attributes") }}</h4>
        <b-alert show variant="warning" dismissible>
            {{ l("Collections are immutable. This means there will be some things you cannot change without creating a new collection. ") }}
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
                <p>WIP Database/Build in here</p>
            </b-tab>
            <b-tab>
                <template v-slot:title> <i class="fa fa-gear"></i>{{ l(" Convert") }}</template>
                <p>WIP Convert Tool in here</p>
            </b-tab>
            <b-tab>
                <template v-slot:title> <i class="fa fa-database"></i>{{ l(" Datatype") }}</template>
                <p>WIP Datatypes in here</p>
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
import _l from "utils/localization";

Vue.use(BootstrapVue);
export default {
    created() {
        this.apiCallToGetData();
    },
    components: {},
    data: function () {
        return {
            collection_data: {}, //all data from the response
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
