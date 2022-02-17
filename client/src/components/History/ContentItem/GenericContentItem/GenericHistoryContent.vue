<template>
    <component :is="providerComponent" :id="data_item.id" auto-refresh v-slot="{ result: item, loading }">
        <div>
            <loading-span v-if="loading" message="Loading dataset" />
            <component :is="renderComponent" v-if="item" :item="item"> </component>
        </div>
    </component>
</template>

<script>
import { DatasetProvider, DatasetCollectionProvider } from "components/providers";
import DatasetCollectionUIWrapper from "./DatasetCollectionUIWrapper";;
import { STATES } from "components/History/model";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        DatasetProvider,
        DatasetCollectionProvider,
        DatasetCollectionUIWrapper,
        LoadingSpan,
    },
    props: {
        data_item: {
            required: true,
        },
    },
    computed: {
        renderComponent() {
            return { hdca: "DatasetCollectionUIWrapper" }[this.data_item.src];
        },
        providerComponent() {
            return { hda: "DatasetProvider", hdca: "DatasetCollectionProvider" }[this.data_item.src];
        },
    },
    provide: {
        STATES,
    },
};
</script>
