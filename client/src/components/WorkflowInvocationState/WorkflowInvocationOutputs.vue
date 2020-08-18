<template>
    <div v-if="dataset">
          <DatasetDisplay
          v-bind:item="dataset"
          v-bind:expanded="expanded"
          v-bind:showTags="true"
          v-on:update:expanded="expand"
          />
    </div>
    <div v-else-if="dataset_collection">
          <CollectionDisplay
          v-bind:item="dataset_collection"
          v-bind:expanded="expanded"
          v-bind:showTags="true"
          v-on:update:expanded="expand"
          />
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import DatasetDisplay from "components/History/ContentItem/Dataset/index"
import CollectionDisplay from "components/History/ContentItem/DatasetCollection/index"
import {Dataset, STATES} from "components/History/model"

import { getAppRoot } from "onload/loadConfig";
import axios from "axios"

import { getRootFromIndexLink } from "onload";
import { mapGetters, mapActions } from "vuex";

const getUrl = (path) => getRootFromIndexLink() + path;

Vue.use(BootstrapVue);

export default {
    components: {
        DatasetDisplay,
        CollectionDisplay,
    },
    props: {
        dataset_id: {
            required: false,
        },
        dataset_collection_id: {
            required: false
        }
    },
    provide: {
        STATES,
    },
    data () {
        return {
            dataset: null,
            dataset_collection: null,
            expanded: false,
        }
    },
    methods: {
        expand(event) {
            console.log('Exapnding'); 
            this.expanded = !this.expanded;
        }
    },
    mounted () {
        if (this.dataset_id) {
           axios.get(
            `${getAppRoot()}api/datasets/${this.dataset_id}`
            ).then(response => (this.dataset = response.data)
        )}
        if (this.dataset_collection_id) {
            axios.get(
            `${getAppRoot()}api/histories/c1ade96b5b4d986d/contents/dataset_collections/${this.dataset_collection_id}`
            ).then(response => (this.dataset_collection = response.data)
        )}
    }
}
</script>