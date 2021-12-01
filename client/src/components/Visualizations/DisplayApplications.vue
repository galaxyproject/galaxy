<template>
    <div>
        <UrlDataProvider :url="url" v-slot="{ result: dataset, loading }">
            <div v-if="dataset && dataset.display_apps">
                {{ dataset.display_apps }}
            </div>
        </UrlDataProvider>
    </div>
</template>
<script>
import { UrlDataProvider } from "components/providers/UrlDataProvider";
export default {
    components: {
        UrlDataProvider,
    },
    props: {
        datasetId: {
            type: String,
            required: true,
        },
    },
    computed: {
        url() {
            return `api/datasets/${this.datasetId}`;
        },
    },
};
</script>
