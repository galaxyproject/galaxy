<template>
    <component :is="providerComponent" :id="data_item.id" v-slot="{ result: item, loading }">
        <div>
            <loading-span v-if="loading" message="Loading dataset" />
            <div v-if="item" :item="item"/>
        </div>
    </component>
</template>

<script>
import { DatasetProvider, DatasetCollectionProvider } from "components/providers";
import { STATES } from "components/History/model";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        DatasetProvider,
        DatasetCollectionProvider,
        LoadingSpan,
    },
    props: {
        data_item: {
            required: true,
        },
    },
    computed: {
        renderComponent() {
            return null; // { hdca: "DatasetCollectionUIWrapper" }[this.data_item.src];
        },
        providerComponent() {
            return null; // { hda: "DatasetProvider", hdca: "DatasetCollectionProvider" }[this.data_item.src];
        },
    },
    provide: {
        STATES,
    },
};
</script>
