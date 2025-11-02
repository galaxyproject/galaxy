<template>
    <PublishedItem :item="visualization">
        <template v-slot>
            <VisualizationFrame :name="visualization.type" :config="visualization.latest_revision.config" />
        </template>
    </PublishedItem>
</template>

<script>
import { urlData } from "@/utils/url";

import VisualizationFrame from "./VisualizationFrame.vue";
import PublishedItem from "@/components/Common/PublishedItem.vue";

export default {
    components: {
        PublishedItem,
        VisualizationFrame,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            visualization: {},
        };
    },
    created() {
        const url = `/api/visualizations/${this.id}`;
        urlData({ url }).then((data) => {
            this.visualization = data;
        });
    },
};
</script>
