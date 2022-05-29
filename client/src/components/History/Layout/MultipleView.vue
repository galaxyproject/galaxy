<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" v-slot="{ currentHistory, histories, handlers, historiesLoading }" :user="user">
            <div v-if="!historiesLoading" id="histories" class="columns-container d-flex flex-row h-100">
                <HistoryPanel
                    :history="currentHistory"
                    class="column current-history p-1 ml-0 mr-1 shadow"
                    v-on="handlers"
                    @view-collection="onViewCollection">
                </HistoryPanel>
                <template v-for="history in histories">
                    <HistoryPanel
                        v-if="history.id !== currentHistory.id"
                        :key="history.id"
                        :history="history"
                        class="column p-1 mx-1"
                        v-on="handlers"
                        @view-collection="onViewCollection">
                    </HistoryPanel>
                </template>
            </div>
            <div v-else class="flex-grow-1 loadingBackground h-100">
                <span v-localize class="sr-only">Loading History...</span>
            </div>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import CurrentUser from "components/providers/CurrentUser";
import UserHistories from "components/providers/UserHistories";
import HistoryPanel from "components/History/CurrentHistory/HistoryPanel";

export default {
    components: {
        CurrentUser,
        UserHistories,
        HistoryPanel,
    },
    methods: {
        onViewCollection(collection) {},
    },
};
</script>

<style lang="scss">
.columns-container > :nth-child(2) {
    margin-left: 19rem !important;
}

.column {
    width: 20%;
    max-width: 18rem;
    min-width: 17rem;
}

.current-history {
    z-index: 10;
    height: 100%;
    position: fixed;
    background: white;
}
</style>
