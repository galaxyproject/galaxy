<template>
    <CurrentUser class="d-flex flex-column" v-slot="{ user }">
        <UserHistories v-if="user" :user="user" v-slot="{ currentHistory, histories, handlers }">
            <div v-if="currentHistory" id="current-history-panel">
                <CurrentHistory
                    v-if="!breadcrumbs.length"
                    :history="currentHistory"
                    v-on="handlers"
                    @viewCollection="onViewCollection">
                    <template v-slot:navigation>
                        <HistoryNavigation
                            v-on="handlers"
                            :histories="histories"
                            :current-history="currentHistory"
                            title="Histories" />
                    </template>
                </CurrentHistory>
                <CurrentCollection
                    v-else-if="breadcrumbs.length"
                    :history="currentHistory"
                    :selected-collections.sync="breadcrumbs"
                    @viewCollection="onViewCollection" />
                <div v-else>
                    <span class="sr-only">Loading...</span>
                </div>
            </div>
            <div v-else class="flex-grow-1 loadingBackground h-100">
                <span class="sr-only" v-localize>Loading History...</span>
            </div>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import CurrentUser from "components/providers/CurrentUser";
import UserHistories from "components/providers/UserHistories";
import HistoryNavigation from "./CurrentHistory/HistoryNavigation";
import CurrentHistory from "./CurrentHistory/HistoryPanel";
import CurrentCollection from "./CurrentCollection/CollectionPanel";

export default {
    components: {
        CurrentUser,
        CurrentHistory,
        CurrentCollection,
        UserHistories,
        HistoryNavigation,
    },
    data() {
        return {
            // list of collections we have drilled down into
            breadcrumbs: [],
        };
    },
    methods: {
        onViewCollection(collection) {
            this.breadcrumbs = [...this.breadcrumbs, collection];
        },
    },
};
</script>
