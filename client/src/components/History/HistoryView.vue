<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" v-slot="{ handlers }" :user="user">
            <div v-if="history" class="d-flex flex-column h-100">
                <b-alert v-if="history.purged" variant="info" show>This history has been purged.</b-alert>
                <div v-else class="flex-row flex-grow-0">
                    <b-button
                        v-if="user.id == history.user_id"
                        size="sm"
                        variant="outline-info"
                        title="Switch to this history"
                        @click="handlers.setCurrentHistory(history)">
                        Switch to this history
                    </b-button>
                    <b-button
                        v-else
                        size="sm"
                        variant="outline-info"
                        title="Import this history"
                        v-b-modal:copy-history-modal>
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
                    v-on="handlers"
                    :history="history"
                    :show-controls="false"
                    @view-collection="onViewCollection" />
                <CopyModal id="copy-history-modal" :history="history" />
            </div>
            <b-alert v-else class="m-2" variant="info" show>
                <LoadingSpan message="Loading History" />
            </b-alert>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import { mapGetters } from "vuex";
import CurrentUser from "components/providers/CurrentUser";
import UserHistories from "components/providers/UserHistories";
import LoadingSpan from "components/LoadingSpan";
import CollectionPanel from "./CurrentCollection/CollectionPanel";
import HistoryPanel from "./CurrentHistory/HistoryPanel";
import CopyModal from "./Modals/CopyModal";

export default {
    components: {
        LoadingSpan,
        HistoryPanel,
        CollectionPanel,
        CurrentUser,
        UserHistories,
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
    created() {
        this.$store.dispatch("history/loadHistoryById", this.id);
    },
    computed: {
        ...mapGetters({ getHistoryById: "history/getHistoryById" }),
        history() {
            return this.getHistoryById(this.id);
        },
    },
    methods: {
        onViewCollection(collection) {
            this.selectedCollections = [...this.selectedCollections, collection];
        },
    },
};
</script>
