<template>
    <component
        :is="providerComponent"
        :id="data_item.id"
        v-slot="{
            item,
            loading,
        }"
    >
        <div>
            <loading-span v-if="loading" message="Loading dataset" />
            <component :is="renderComponent" v-if="item" :item="item" v-bind:index="1" v-bind:showTags="true">
            </component>
        </div>
    </component>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import { DatasetProvider, DatasetCollectionProvider } from "./providers";
import HistoryContentItem from "components/History/ContentItem";
import DatasetCollectionUIWrapper from "./DatasetCollectionUIWrapper";
import DatasetUIWrapper from "./DatasetUIWrapper";
import { STATES } from "components/History/model";
import LoadingSpan from "components/LoadingSpan";

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
        data_item: {
            required: true,
        },
    },
    computed: {
        renderComponent() {
            return { hda: "DatasetUIWrapper", hdca: DatasetCollectionUIWrapper }[this.data_item.src];
        },
        providerComponent() {
            return { hda: "DatasetProvider", hdca: DatasetCollectionProvider }[this.data_item.src];
        },
    },
    provide: {
        STATES,
    },
};
</script>
