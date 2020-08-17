<template>
    <div v-if="dataset">
        <index v-bind:item="dataset" v-bind:expanded="false"/>
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
            dataset: null
        }
    },
    mounted () {
           axios.get(
            `${getAppRoot()}api/datasets/${this.dataset_id}`
            ).then(response => (this.dataset = response.data)
            )}
}
</script>