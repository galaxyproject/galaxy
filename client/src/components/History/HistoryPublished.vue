<template>
    <Published :item="history">
        <template v-slot>
            <HistoryView :id="id" />
        </template>
    </Published>
</template>

<script>
import Published from "components/Common/Published";
import HistoryView from "components/History/HistoryView";
import { urlData } from "utils/url";

export default {
    components: {
        Published,
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
