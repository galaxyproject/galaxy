<!-- A single history panel is either showing the history or one of the
selected datset collections -->

<template>
    <HistoryComponent v-if="history && !selectedCollections.length" :history="history" v-on="$listeners">
        <template v-for="(_, name) in $scopedSlots" :slot="name" slot-scope="slotData">
            <slot :name="name" v-bind="slotData" :history="history" />
        </template>
    </HistoryComponent>

    <!-- <pre v-if="history && !selectedCollections.length">{{ history }}</pre> -->

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
import HistoryComponent from "./History";
import SelectedCollection from "./SelectedCollection/Panel";
import { History, STATES } from "./model";

export default {
    components: {
        HistoryComponent,
        SelectedCollection,
    },
    props: {
        history: { type: History, required: true },
    },
    data() {
        return {
            selectedCollections: [],
        };
    },
    provide: {
        STATES,
    },
    methods: {
        selectCollection(coll) {
            this.selectedCollections = [...this.selectedCollections, coll];
        },
    },
    mounted() {
        this.eventHub.$on("selectCollection", this.selectCollection);
    },
};
</script>
