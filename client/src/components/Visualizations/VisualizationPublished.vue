<template>
    <Published :item="visualization">
        <template v-slot>
            <CenterFrame :src="getUrl" />
        </template>
    </Published>
</template>

<script>
import Published from "components/Common/Published";
import CenterFrame from "entry/analysis/modules/CenterFrame";
import { urlData } from "utils/url";

export default {
    components: {
        CenterFrame,
        Published,
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
