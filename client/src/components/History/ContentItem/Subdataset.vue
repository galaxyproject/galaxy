<!-- a dataset contained inside a collection, the api is different, so we're going to need to dig up
the data for the dataset on-click 

<DatasetProvider :item="item" v-slot="{ dataset }"></DatasetProvider>
-->

<template>
    <DatasetProvider :item="item" v-slot="{ dataset, load }">
        <DatasetUI
            v-if="dataset"
            v-bind="$attrs"
            v-on="$listeners"
            :dataset="dataset"
            :expanded="expanded"
            :writable="false"
            @update:expanded="load"
        />
    </DatasetProvider>
</template>

<script>
import { DatasetProvider } from "../providers";
import { DatasetUI } from "./Dataset";

export default {
    components: {
        DatasetProvider,
        DatasetUI,
    },
    props: {
        item: { type: Object, required: true },
        index: { type: Number, required: true },
        expanded: { type: Boolean, required: true },
        writable: { type: Boolean, required: true },
    },
};
</script>
