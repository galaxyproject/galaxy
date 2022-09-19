<template>
    <div id="list-item" class="d-flex flex-column align-items-center w-100">
        <CollectionPanel
            v-if="selectedCollections.length && selectedCollections[0].history_id === source.id"
            :history="getHistory"
            :selected-collections.sync="selectedCollections"
            :show-controls="false"
            @view-collection="onViewCollection" />
        <HistoryPanel
            v-else
            :history="getHistory"
            :filter="filter"
            :show-controls="false"
            v-on="handlers"
            @view-collection="onViewCollection" />
        <hr class="w-100 m-2" />
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
import { mapGetters } from "vuex";
import HistoryPanel from "components/History/CurrentHistory/HistoryPanel";
import CollectionPanel from "components/History/CurrentCollection/CollectionPanel";

export default {
    components: {
        HistoryPanel,
        CollectionPanel,
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
        ...mapGetters({ getHistoryById: "history/getHistoryById" }),
        sameToCurrent() {
            return this.currentHistory.id === this.source.id;
        },
        getHistory() {
            return this.getHistoryById(this.source.id);
        },
    },
    methods: {
        onViewCollection(collection) {
            this.selectedCollections = [...this.selectedCollections, collection];
        },
    },
};
</script>
