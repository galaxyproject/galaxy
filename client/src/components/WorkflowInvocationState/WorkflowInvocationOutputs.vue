<template>
    <div v-if="dataset">
        <span v-on:click="expand">
            <index v-bind:item="dataset" v-bind:expanded="expanded" v-bind:showTags="true"/>
        </span>
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import index from "components/History/ContentItem/Dataset/index"
import {Dataset, STATES} from "components/History/model"

import { getAppRoot } from "onload/loadConfig";
import axios from "axios"

import { getRootFromIndexLink } from "onload";
import { mapGetters, mapActions } from "vuex";

const getUrl = (path) => getRootFromIndexLink() + path;

Vue.use(BootstrapVue);

export default {
    components: {
        index,
    },
    props: {
        dataset_id: {
            required: true,
        }
    },
    provide: {
        STATES,
    },
    data () {
        return {
            dataset: null,
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
           axios.get(
            `${getAppRoot()}api/datasets/${this.dataset_id}`
            ).then(response => (this.dataset = response.data)
            )}
}
</script>