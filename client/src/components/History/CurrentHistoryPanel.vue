<template>
    <CurrentUser class="d-flex flex-column" v-slot="{ user }">
        <UserHistories v-if="user" :user="user" v-slot="{ currentHistory, histories, handlers }">
            <HistoryPanel v-if="currentHistory" :history="currentHistory" v-on="handlers">
                <template v-slot:nav>
                    <div>
                        <HistorySelector
                            :histories="histories"
                            :current-history="currentHistory"
                            :show-modal="showModal"
                            @update:currentHistory="handlers.setCurrentHistory"
                            @hideModal="showModalHandler"
                        />
                        <HistoriesMenu v-on="handlers" @selectHistoryModal="showModalHandler" />
                    </div>
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
import HistorySelector from "./HistorySelector";
import HistoriesMenu from "./HistoriesMenu";

export default {
    components: {
        CurrentUser,
        UserHistories,
        HistoryPanel,
        HistorySelector,
        HistoriesMenu,
    },
    data() {
        return {
            showModal: false,
        };
    },
    methods: {
        showModalHandler(event) {
            this.showModal = !this.showModal;
        },
    },
};
</script>
