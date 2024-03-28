<template>
    <div v-if="currentUser && history" class="d-flex flex-column h-100">
        <b-alert v-if="showHistoryStateInfo" variant="info" show data-description="history state info">
            {{ historyStateInfoMessage }}
        </b-alert>

        <div class="flex-row flex-grow-0 pb-3">
            <b-button
                v-if="userOwnsHistory"
                size="sm"
                variant="outline-info"
                :title="setAsCurrentTitle"
                :disabled="isSetAsCurrentDisabled"
                data-description="switch to history button"
                @click="setCurrentHistory(history.id)">
                Switch to this history
            </b-button>

            <b-button
                v-if="canImportHistory"
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
            :can-edit-history="canEditHistory"
            filterable
            @view-collection="onViewCollection" />

        <CopyModal id="copy-history-modal" :history="history" />
    </div>
</template>

<script>
import { mapActions, mapState } from "pinia";

import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

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
        isCurrentHistory() {
            return this.currentHistory?.id == this.history?.id;
        },
        isSetAsCurrentDisabled() {
            return this.isCurrentHistory || this.history.archived || this.history.purged;
        },
        setAsCurrentTitle() {
            if (this.isCurrentHistory) {
                return "This history is already your current history.";
            }
            if (this.history.archived) {
                return "This history has been archived and cannot be set as your current history. Unarchive it first.";
            }
            if (this.history.purged) {
                return "This history has been purged and cannot be set as your current history.";
            }
            return "Switch to this history";
        },
        canEditHistory() {
            return this.userOwnsHistory && !this.history.archived && !this.history.purged;
        },
        showHistoryArchived() {
            return this.history.archived && this.userOwnsHistory;
        },
        showHistoryStateInfo() {
            return this.showHistoryArchived || this.history.purged;
        },
        historyStateInfoMessage() {
            if (this.showHistoryArchived && this.history.purged) {
                return "This history has been archived and purged.";
            } else if (this.showHistoryArchived) {
                return "This history has been archived.";
            } else if (this.history.purged) {
                return "This history has been purged.";
            }
            return "";
        },
        canImportHistory() {
            return !this.userOwnsHistory && !this.history.purged;
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
