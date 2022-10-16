<template>
    <Published :item="visualization" @set-rating="onSetRating">
        <template v-slot>
            <CenterFrame :src="getUrl" />
        </template>
    </Published>
</template>

<script>
import { urlData } from "utils/url";
import CenterFrame from "entry/analysis/modules/CenterFrame";
import Published from "components/Common/Published";
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
        const query = this.$route.query;
        urlData({ url }).then((data) => {
            this.visualization = { ...data, ...query };
        });
    },
    methods: {
        onSetRating(newRating) {
            const url = `/visualization/rate_async?id=${this.id}&rating=${newRating}`;
            urlData({ url });
        },
    },
};
</script>
