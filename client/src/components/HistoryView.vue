<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" v-slot="{ handlers }" :user="user">
            <div v-if="getHistory" class="d-flex flex-column h-100">
                <CollectionPanel
                    v-if="selectedCollections.length && selectedCollections[0].history_id == id"
                    :history="getHistory"
                    :selected-collections.sync="selectedCollections"
                    :show-controls="false"
                    @view-collection="onViewCollection" />
                <HistoryPanel
                    v-else
                    v-on="handlers"
                    :history="getHistory"
                    :show-controls="false"
                    @view-collection="onViewCollection" />
            </div>
            <b-alert v-else class="m-2" variant="info" show>
                <LoadingSpan message="Loading Histories" />
            </b-alert>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import { mapGetters } from "vuex";
import CollectionPanel from "components/History/CurrentCollection/CollectionPanel";
import CurrentUser from "components/providers/CurrentUser";
import HistoryPanel from "components/History/CurrentHistory/HistoryPanel";
import LoadingSpan from "components/LoadingSpan";
import UserHistories from "components/providers/UserHistories";

export default {
    components: {
        LoadingSpan,
        HistoryPanel,
        CollectionPanel,
        CurrentUser,
        UserHistories,
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
        ...mapGetters({ getHistoryById: "history/getHistoryById" }),
        getHistory() {
            console.log(this.id);
            console.log(this.getHistoryById(this.id));
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
