<template>
    <CurrentUser class="d-flex flex-column" v-slot="{ user }">
        <UserHistories v-if="user" :user="user" v-slot="{ currentHistory, histories, handlers }">
            <HistoryPanel v-if="currentHistory" :history="currentHistory" v-on="handlers" id="current-history-panel">
                <template v-slot:globalNav>
                    <HistoriesMenu
                        v-on="handlers"
                        :histories="histories"
                        :current-history="currentHistory"
                        title="Histories" />
                </template>
            </HistoryPanel>

            <div v-else class="flex-grow-1 loadingBackground h-100">
                <span class="sr-only" v-localize>Loading History...</span>
            </div>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import CurrentUser from "components/providers/CurrentUser";
import UserHistories from "./providers/UserHistories";
import HistoryPanel from "./HistoryPanel";
import HistoriesMenu from "./HistoriesMenu";

export default {
    components: {
        CurrentUser,
        UserHistories,
        HistoryPanel,
        HistoriesMenu,
    },
};
</script>
