<template>
    <div v-if="historyId">
        <HistorySelector v-model="historyId" />

        <PriorityMenu style="max-width: 50%;" :starting-height="27">
            <PriorityMenuItem
                key="create-new-history"
                title="Create New History"
                icon="fa fa-plus"
                @click="createHistory"
            />

            <PriorityMenuItem
                key="view-all-histories"
                title="View All Histories"
                icon="fa fa-columns"
                @click="redirect('/history/view_multiple')"
            />

            <PriorityMenuItem
                key="saved-histories"
                title="Saved Histories"
                icon="fas fa-save"
                @click="backboneRoute('/histories/list')"
            />

            <PriorityMenuItem
                key="clear-history-cache"
                title="Clear cache"
                icon="fa fa-refresh"
                @click.stop="clearCache"
            />

            <PriorityMenuItem
                key="use-legacy-history"
                title="Return to legacy history panel"
                icon="fas fa-exchange-alt"
                @click="switchToLegacyHistoryPanel"
            />
        </PriorityMenu>
    </div>
</template>

<script>
import { mapActions } from "vuex";
import { PriorityMenuItem, PriorityMenu } from "components/PriorityMenu";
import HistorySelector from "./HistorySelector";
import { createNewHistory } from "./model/queries";
import { wipeDatabase, clearHistoryDateStore } from "./caching";
import { legacyNavigationMixin } from "components/plugins";
import { switchToLegacyHistoryPanel } from "./adapters/betaToggle";

export default {
    mixins: [legacyNavigationMixin],
    components: {
        PriorityMenu,
        PriorityMenuItem,
        HistorySelector,
    },
    props: {
        selectedHistoryId: { type: String, required: false, default: null },
    },
    computed: {
        historyId: {
            get() {
                return this.selectedHistoryId;
            },
            set(id) {
                this.$emit("update:selectedHistoryId", id);
            },
        },
    },
    methods: {
        ...mapActions("betaHistory", ["storeHistory"]),

        switchToLegacyHistoryPanel,

        // create new server, store in vuex, switch to it
        async createHistory() {
            const newHistory = await createNewHistory();
            await this.storeHistory(newHistory);
            this.historyId = newHistory.id;
        },

        async clearCache() {
            await wipeDatabase();
            await clearHistoryDateStore();
        },
    },
};
</script>
