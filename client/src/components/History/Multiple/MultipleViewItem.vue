<template>
    <div v-if="!getHistory" class="container">
        <div class="row align-items-center h-100">
            <LoadingSpan class="mx-auto" message="Loading History" />
        </div>
    </div>
    <div v-else id="list-item" class="d-flex flex-column align-items-center w-100">
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
            @view-collection="onViewCollection" />
        <hr class="w-100 m-2" />
        <div class="flex-row flex-grow-0">
            <b-button
                size="sm"
                class="my-1"
                :disabled="sameToCurrent"
                :variant="sameToCurrent ? 'disabled' : 'outline-info'"
                :title="sameToCurrent ? 'Current History' : 'Switch to this history'"
                @click="setCurrentHistory(source.id)">
                {{ sameToCurrent ? "Current History" : "Switch to" }}
            </b-button>
            <b-button
                size="sm"
                class="my-1"
                variant="outline-danger"
                title="Hide this history from the list"
                @click="unpinHistory(source.id)">
                Hide
            </b-button>
        </div>
    </div>
</template>

<script>
import { mapActions, mapState } from "pinia";
import { useHistoryStore } from "@/stores/historyStore";
import HistoryPanel from "components/History/CurrentHistory/HistoryPanel";
import CollectionPanel from "components/History/CurrentCollection/CollectionPanel";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        HistoryPanel,
        CollectionPanel,
        LoadingSpan,
    },
    props: {
        source: {
            type: Object,
            required: true,
        },
        filter: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            selectedCollections: [],
        };
    },
    computed: {
        ...mapState(useHistoryStore, ["currentHistoryId", "getHistoryById"]),
        sameToCurrent() {
            return this.currentHistoryId === this.source.id;
        },
        getHistory() {
            return this.getHistoryById(this.source.id);
        },
    },
    methods: {
        ...mapActions(useHistoryStore, ["setCurrentHistory", "unpinHistory"]),
        onViewCollection(collection) {
            this.selectedCollections = [...this.selectedCollections, collection];
        },
    },
};
</script>
