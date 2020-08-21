<template>
    <div v-if="dataset_id">
        <DatasetProvider
            :id="dataset_id"
            v-slot="{
                item,
                loading,
            }"
        >
            <div>
                <loading-span v-if="loading" message="Loading datasets" />
                <DatasetUIWrapper
                   v-if="item"
                   :item="item"
                   v-bind:index="1"
                   v-bind:showTags="true"
                   >
                </DatasetUIWrapper>
            </div>
        </DatasetProvider>
    </div>
    <div v-else-if="dataset_collection_id">
        <DatasetCollectionProvider
            :id="dataset_collection_id"
            v-slot="{
                item,
                loading,
            }">
            <div>
                <loading-span v-if="loading" message="Loading collections" />
                <DatasetCollectionUIWrapper
                   v-if="item"
                   :item="item"
                   v-bind:index="1"
                   v-bind:showTags="true"
                   >
                </DatasetCollectionUIWrapper>
            </div>
         </DatasetCollectionProvider>
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import {DatasetProvider, DatasetCollectionProvider} from "components/History/providers/DatasetProvider";
import HistoryContentItem from "components/History/ContentItem/HistoryContentItem";
import DatasetCollectionUIWrapper from "components/History/ContentItem/DatasetCollection/DatasetCollectionUIWrapper";
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
        DatasetCollectionProvider,
        DatasetUIWrapper,
        DatasetCollectionUIWrapper,
        LoadingSpan,
        HistoryContentItem,
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
        };
    },
};
</script>
