<template>
    <div v-if="currentUser && currentHistory" id="current-history-panel" class="d-flex flex-column history-index">
        <HistoryPanel
            v-if="!breadcrumbs.length"
            :list-offset="listOffset"
            :history="currentHistory"
            :filterable="true"
            @view-collection="onViewCollection">
            <template v-slot:navigation>
                <HistoryNavigation
                    :history="currentHistory"
                    :histories="histories"
                    :histories-loading="historiesLoading"
                    title="Histories" />
            </template>
        </HistoryPanel>
        <CurrentCollection
            v-else-if="breadcrumbs.length"
            :history="currentHistory"
            :selected-collections.sync="breadcrumbs"
            @view-collection="onViewCollection" />
        <div v-else>
            <span class="sr-only">Loading...</span>
        </div>
    </div>
    <div v-else class="flex-grow-1 loadingBackground h-100">
        <span v-localize class="sr-only">Loading History...</span>
    </div>
</template>

<script>
import { mapState } from "pinia";
import { useUserStore } from "@/stores/userStore";
import { useHistoryStore } from "@/stores/historyStore";
import HistoryNavigation from "./CurrentHistory/HistoryNavigation";
import HistoryPanel from "./CurrentHistory/HistoryPanel";
import CurrentCollection from "./CurrentCollection/CollectionPanel";

export default {
    components: {
        HistoryPanel,
        CurrentCollection,
        HistoryNavigation,
    },
    data() {
        return {
            // list of collections we have drilled down into
            breadcrumbs: [],
            listOffset: 0,
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        ...mapState(useHistoryStore, ["currentHistory", "histories", "historiesLoading"]),
    },
    methods: {
        onViewCollection(collection, currentOffset) {
            this.listOffset = currentOffset;
            this.breadcrumbs = [...this.breadcrumbs, collection];
        },
    },
};
</script>
