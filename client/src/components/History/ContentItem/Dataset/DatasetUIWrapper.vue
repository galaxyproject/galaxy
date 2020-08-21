<template>
    <DatasetUI
        v-if="dataset"
        v-bind="$attrs"
        v-on="$listeners"
        v-on:update:expanded="expand"
        :expanded="expanded"
        :dataset="dataset"
        :showTags="true">
    </DatasetUI>
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
    data() {
        return {
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
