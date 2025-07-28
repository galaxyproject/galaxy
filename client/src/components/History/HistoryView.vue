<template>
    <div v-if="currentUser && history" class="d-flex flex-column h-100">
        <BreadcrumbHeading :items="breadcrumbItems">
            <div class="d-flex flex-gapx-1">
                <GButton
                    v-if="userOwnsHistory"
                    color="blue"
                    :title="setAsCurrentTitle"
                    :disabled="isSetAsCurrentDisabled"
                    data-description="switch to history button"
                    @click="setCurrentHistory(history.id)">
                    Switch to this history
                </GButton>

                <GButton
                    v-if="canImportHistory"
                    v-b-modal:copy-history-modal
                    color="blue"
                    title="Import this history"
                    data-description="import history button">
                    <FontAwesomeIcon :icon="faFileImport" />
                    Import this history
                </GButton>

                <HistoryOptions :history="history" minimal />
            </div>
        </BreadcrumbHeading>

        <b-alert :show="copySuccess">
            History imported and is now your active history. <b-link :to="importedHistoryLink">View here</b-link>.
        </b-alert>

        <CollectionPanel
            v-if="selectedCollections.length && selectedCollections[0].history_id == id"
            :history="history"
            :selected-collections.sync="selectedCollections"
            :show-controls="false"
            @view-collection="onViewCollection" />
        <HistoryPanel v-else :history="history" filterable @view-collection="onViewCollection" />

        <CopyModal id="copy-history-modal" :history="history" @ok="copyOkay" />
    </div>
</template>

<script>
import FontAwesomeIcon from "@fortawesome/vue-fontawesome";
import { mapActions, mapState } from "pinia";

import { isAnonymousUser } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import CollectionPanel from "./CurrentCollection/CollectionPanel";
import HistoryPanel from "./CurrentHistory/HistoryPanel";
import CopyModal from "./Modals/CopyModal";

import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import HistoryOptions from "@/components/History/HistoryOptions.vue";

export default {
    components: {
        HistoryPanel,
        CollectionPanel,
        CopyModal,
        FontAwesomeIcon,
        GButton,
        BreadcrumbHeading,
        HistoryOptions,
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
            copySuccess: false,
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        ...mapState(useHistoryStore, ["getHistoryById", "currentHistory"]),
        breadcrumbItems() {
            return [
                { title: "Histories", to: "/histories/list" },
                {
                    title: this.history.name,
                    to: `/histories/view?id=${this.history.id}`,
                    superText: this.isCurrentHistory ? "current" : undefined,
                },
            ];
        },
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
            return this.isCurrentHistory;
        },
        setAsCurrentTitle() {
            if (this.isCurrentHistory) {
                return "This history is already your current history.";
            }
            return "Switch to this history";
        },
        canImportHistory() {
            return !this.userOwnsHistory && !this.history.purged;
        },
        importedHistoryLink() {
            return isAnonymousUser(this.currentUser) ? "/" : "/histories/list";
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
        copyOkay() {
            this.copySuccess = true;
        },
    },
};
</script>
