<template>
    <div v-if="dataset_id">
        <DatasetProvider
            :id="dataset_id"
            v-slot="{
                dataset,
                loading,
            }"
        >
            <div>
            <loading-span v-if="loading" message="Loading datasets" />
            <DatasetUIWrapper
               v-if="dataset"
               :item="dataset"
               v-bind:expanded="expanded"
               v-bind:index="1"
               v-bind:showTags="true"
               v-on:update:expanded="expand"
               >
            </DatasetUIWrapper>
            </div>
        </DatasetProvider>
    </div>
    <div v-else-if="dataset_collection">
        <HistoryContentItem
            v-bind:item="dataset_collection"
            v-bind:expanded="expanded"
            v-bind:index="1"
            v-bind:showTags="true"
            v-on:update:expanded="expand"
        />
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import DatasetProvider from "components/History/providers/DatasetProvider";
import HistoryContentItem from "components/History/ContentItem/HistoryContentItem";
import DatasetUIWrapper from "components/History/ContentItem/Dataset/DatasetUIWrapper";
import { Dataset, STATES } from "components/History/model";
import LoadingSpan from "components/LoadingSpan";

import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

import { getRootFromIndexLink } from "onload";
import { mapGetters, mapActions } from "vuex";

const getUrl = (path) => getRootFromIndexLink() + path;

Vue.use(BootstrapVue);

export default {
    components: {
        DatasetProvider,
        DatasetUIWrapper,
        LoadingSpan,
    },
    props: {
        dataset_id: {
            required: false,
        },
        dataset_collection_id: {
            required: false,
        },
    },
    provide: {
        STATES,
    },
    data() {
        return {
            dataset_collection: null,
            expanded: false,
        };
    },
    methods: {
        expand(event) {
            console.log("Exapnding");
            this.expanded = !this.expanded;
        },
    },
};
</script>
