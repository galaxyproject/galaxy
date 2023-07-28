<template>
    <PublishedItem :item="visualization">
        <template v-slot>
            <CenterFrame :src="getUrl" />
        </template>
    </PublishedItem>
</template>

<script>
import { urlData } from "@/utils/url";

import PublishedItem from "@/components/Common/PublishedItem.vue";
import CenterFrame from "@/entry/analysis/modules/CenterFrame.vue";

export default {
    components: {
        CenterFrame,
        PublishedItem,
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
    computed: {
        getUrl() {
            return `/visualization/saved?id=${this.id}`;
        },
    },
    created() {
        const url = `/api/visualizations/${this.id}`;
        urlData({ url }).then((data) => {
            this.visualization = data;
        });
    },
};
</script>
