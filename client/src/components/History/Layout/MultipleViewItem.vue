<template>
    <div class="d-flex flex-column align-items-center">
        <CurrentCollection
            v-if="selectedCollections.length && selectedCollections[0].history_id === source.id"
            :history="currentHistory"
            :selected-collections.sync="selectedCollections"
            @view-collection="onViewCollection" />
        <HistoryPanel v-else :history="source" :filter="filter" v-on="handlers" @view-collection="onViewCollection">
        </HistoryPanel>

        <div class="flex-row flex-grow-0">
            <b-button
                size="sm"
                class="my-1"
                :disabled="sameToCurrent"
                :variant="sameToCurrent ? 'disabled' : 'outline-info'"
                :title="sameToCurrent ? 'Current History' : 'Switch to this history'"
                @click="handlers.setCurrentHistory(source)">
                {{ sameToCurrent ? "Current History" : "Switch to" }}
            </b-button>
            <b-button
                size="sm"
                class="my-1"
                variant="outline-danger"
                title="Hide this history from the list"
                @click="removeHistoryFromList(source)">
                Hide
            </b-button>
        </div>
    </div>
</template>

<script>
import HistoryPanel from "components/History/CurrentHistory/HistoryPanel";
import CurrentCollection from "components/History/CurrentCollection/CollectionPanel";

export default {
    components: {
        HistoryPanel,
        CurrentCollection,
    },
    props: {
        source: {
            type: Object,
            required: true,
        },
        currentHistory: {
            type: Object,
            required: true,
        },
        handlers: {
            type: Object,
            required: true,
        },
        filter: {
            type: String,
            default: null,
        },
        removeHistoryFromList: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            selectedCollections: [],
        };
    },
    computed: {
        sameToCurrent() {
            return this.currentHistory.id === this.source.id;
        },
    },
    methods: {
        onViewCollection(collection) {
            this.selectedCollections = [...this.selectedCollections, collection];
        },
    },
};
</script>
