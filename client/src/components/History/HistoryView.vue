<template>
    <div v-if="currentUser && history" class="d-flex flex-column h-100">
        <b-alert v-if="history.purged" variant="info" show>This history has been purged.</b-alert>
        <div v-else class="flex-row flex-grow-0">
            <b-button
                v-if="currentUser.id == history.user_id"
                size="sm"
                variant="outline-info"
                title="Switch to this history"
                :disabled="currentHistory.id == history.id"
                @click="setCurrentHistory(history)">
                Switch to this history
            </b-button>
            <b-button v-else v-b-modal:copy-history-modal size="sm" variant="outline-info" title="Import this history">
                Import this history
            </b-button>
        </div>
        <CollectionPanel
            v-if="selectedCollections.length && selectedCollections[0].history_id == id"
            :history="history"
            :selected-collections.sync="selectedCollections"
            :show-controls="false"
            @view-collection="onViewCollection" />
        <HistoryPanel
            v-else
            :history="history"
            :writable="currentUser.id == history.user_id"
            :show-controls="false"
            @view-collection="onViewCollection" />
        <CopyModal id="copy-history-modal" :history="history" />
    </div>
</template>

<script>
import { mapActions, mapState } from "pinia";
import { useUserStore } from "@/stores/userStore";
import { useHistoryStore } from "@/stores/historyStore";
import CollectionPanel from "./CurrentCollection/CollectionPanel";
import HistoryPanel from "./CurrentHistory/HistoryPanel";
import CopyModal from "./Modals/CopyModal";

export default {
    components: {
        HistoryPanel,
        CollectionPanel,
        CopyModal,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            selectedCollections: [],
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        ...mapState(useHistoryStore, ["getHistoryById", "currentHistory"]),
        history() {
            return this.getHistoryById(this.id);
        },
    },
    created() {
        this.loadHistoryById(this.id);
    },
    methods: {
        ...mapActions(useHistoryStore, ["loadHistoryById", "setCurrentHistory"]),
        onViewCollection(collection) {
            this.selectedCollections = [...this.selectedCollections, collection];
        },
    },
};
</script>
