<template>
    <div>
        <p v-html="contentDetails" />
    </div>
</template>

<script>
import { urlData } from "utils/url";
export default {
    props: {
        pageId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            contentDetails: {},
        };
    },
    created() {
        const url = `/page/display_html?id=${this.pageId}`;
        urlData({ url }).then((data) => {
            this.contentDetails = data;
        });
    },
};
</script>
