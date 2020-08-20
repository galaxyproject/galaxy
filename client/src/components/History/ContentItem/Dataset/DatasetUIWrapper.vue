<template>
    <DatasetUI v-if="dataset" v-bind="$attrs" v-on="$listeners" :dataset="dataset" :showTags="true"/>
</template>
<script>
import DatasetUI from "./DatasetUI";
import { Dataset } from "../../model/Dataset";
export default {
    components: {
        DatasetUI,
    },
    props: {
        item: { type: Object, required: true },
    },
    computed: {
        dataset() {
            return new Dataset(this.item);
        },
    },
};
</script>
