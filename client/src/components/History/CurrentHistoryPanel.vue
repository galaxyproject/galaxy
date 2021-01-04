<template>
    <HistoryPanel v-if="historyId" :history-id="historyId">
        <template v-slot:nav>
            <HistoryTopNav :selected-history-id.sync="historyId" />
        </template>
    </HistoryPanel>
    <div v-else class="flex-grow-1 loadingBackground h-100">
        <span class="sr-only">Loading History...</span>
    </div>
</template>

<script>
import { mapActions, mapGetters } from "vuex";
import HistoryTopNav from "./HistoryTopNav";
import HistoryPanel from "./HistoryPanel";

export default {
    components: {
        HistoryPanel,
        HistoryTopNav,
    },
    computed: {
        ...mapGetters("betaHistory", ["currentHistoryId"]),

        historyId: {
            get() {
                return this.currentHistoryId;
            },
            set(newId) {
                this.storeCurrentHistoryId(newId);
            },
        },
    },
    methods: {
        ...mapActions("betaHistory", ["storeCurrentHistoryId"]),
    },
};
</script>
