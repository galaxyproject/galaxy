<!-- A single history panel is either showing the history or one of the
selected datset collections -->

<template>
    <History
        v-on:select-collection="selectCollection($event)"
        v-if="history && !selectedCollections.length"
        :history="history"
    >
        <template v-for="(_, name) in $scopedSlots" :slot="name" slot-scope="slotData">
            <slot :name="name" v-bind="slotData" :history="history" />
        </template>
    </History>

    <SelectedCollection
        v-else-if="selectedCollections.length"
        :history="history"
        :selected-collections.sync="selectedCollections"
    />

    <div v-else>
        <span class="sr-only">Loading...</span>
    </div>
</template>

<script>
import { mapGetters } from "vuex";
import History from "./History";
import SelectedCollection from "./SelectedCollection/Panel";
import { STATES } from "./model";

export default {
    components: {
        History,
        SelectedCollection,
    },
    props: {
        historyId: { type: String, required: true },
    },
    data: () => ({
        selectedCollections: [],
    }),
    provide: {
        STATES,
    },
    computed: {
        ...mapGetters("betaHistory", ["getHistoryById"]),
        history() {
            return this.getHistoryById(this.historyId);
        },
    },
    methods: {
        selectCollection(coll) {
            this.selectedCollections = [...this.selectedCollections, coll];
        },
    },
};
</script>
