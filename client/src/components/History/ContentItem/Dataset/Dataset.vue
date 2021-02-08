<template>
    <DatasetUI
        v-if="dataset"
        v-bind="$attrs"
        v-on="$listeners"
        :dataset="dataset"
        @update:dataset="$emit('update:item', $event)"
    />
</template>

<script>
import DatasetUI from "./DatasetUI";
import { Dataset } from "../../model";

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
