<template>
    <div v-if="currentUser && history" class="d-flex flex-column h-100">
        <b-alert v-if="history.archived" variant="warning" show>This history has been archived.</b-alert>
        <b-alert v-if="history.purged" variant="info" show data-description="history is purged">
            This history has been purged.
        </b-alert>
        <div v-else class="flex-row flex-grow-0 pb-3">
            <b-button
                v-if="userOwnsHistory"
                size="sm"
                variant="outline-info"
                title="Switch to this history"
                :disabled="isSetAsCurrentDisabled"
                data-description="switch to history button"
                @click="setCurrentHistory(history.id)">
                Switch to this history
            </b-button>
            <b-button
                v-else
                v-b-modal:copy-history-modal
                size="sm"
                variant="outline-info"
                title="Import this history"
                data-description="import history button">
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
            :writable="canEditHistory"
            :show-controls="false"
            filterable
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
        userOwnsHistory() {
            return this.currentUser.id == this.history.user_id;
        },
        isSetAsCurrentDisabled() {
            return this.currentHistory.id == this.history.id || this.history.archived || this.history.purged;
        },
        canEditHistory() {
            return this.userOwnsHistory && !this.history.archived && !this.history.purged;
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
