<template>
    <PublishedItem :item="history">
        <template v-slot>
            <HistoryView :id="id" />
        </template>
    </PublishedItem>
</template>

<script>
import { urlData } from "utils/url";

import PublishedItem from "@/components/Common/PublishedItem.vue";
import HistoryView from "@/components/History/HistoryView.vue";

export default {
    components: {
        PublishedItem,
        HistoryView,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            history: {},
        };
    },
    created() {
        const url = `/api/histories/${this.id}`;
        urlData({ url }).then((data) => {
            this.history = data;
        });
    },
};
</script>
