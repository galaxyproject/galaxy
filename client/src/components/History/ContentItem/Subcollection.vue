<!-- a separate collection content item for collections
    inside of other collections -->

<template>
    <DscUI v-if="dsc" v-bind="$attrs" v-on="$listeners" class="dataset-collection history-content" :dsc="dsc" />
</template>

<script>
import { DatasetCollection } from "../model/DatasetCollection";
import { STATES } from "../model";
import DscUI from "./DatasetCollection/DscUI";

export default {
    components: {
        DscUI,
    },
    props: {
        item: { type: Object, required: true },
    },
    computed: {
        dsc() {
            // TODO: I'm sure this is not the right way to set the state, but the collection api
            // doesn't return any kind of state value at because the api is inconsistent
            // /api/dataset_collections/d071e794759ab192/contents/e144222fed44799a
            return new DatasetCollection({ ...this.item, populated_state: STATES.OK });
        },
    },
};
</script>
