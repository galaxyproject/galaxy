<template>
    <div class="d-flex flex-column align-items-center">
        <HistoryPanel :history="source" v-on="handlers" @view-collection="onViewCollection" />
        <b-button
            size="sm"
            class="my-1"
            :disabled="sameToCurrent"
            :variant="sameToCurrent ? 'disabled' : 'outline-info'"
            :title="sameToCurrent ? 'Current History' : 'Switch to this history'"
            @click="handlers.setCurrentHistory(source)">
            {{ sameToCurrent ? "Current History" : "Switch to" }}
        </b-button>
    </div>
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
        currentHistoryId: {
            type: String,
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
    computed: {
        sameToCurrent() {
            return this.currentHistoryId === this.source.id;
        },
    },
};
</script>
