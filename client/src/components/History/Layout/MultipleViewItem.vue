<template>
    <HistoryPanel :history="source" v-on="handlers" @view-collection="onViewCollection" />
</template>

<script>
import HistoryPanel from "components/History/CurrentHistory/HistoryPanel";

export default {
    components: { HistoryPanel },
    props: {
        source: {
            type: Object,
            required: true,
        },
        handlers: {
            type: Object,
            required: true,
        },
        onViewCollection: {
            type: Function,
            required: true,
        },
    },
};
</script>
