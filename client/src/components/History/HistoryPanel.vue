<!-- A single history panel is either showing the history or one of the
selected datset collections -->

<template>
    <HistoryComponent
        v-if="history && !breadcrumbs.length"
        :history="history"
        v-on="$listeners"
        @viewCollection="drillDown">
        <template v-for="(_, name) in $scopedSlots" :slot="name" slot-scope="slotData">
            <slot :name="name" v-bind="slotData" :history="history" />
        </template>
    </HistoryComponent>

    <CurrentCollection
        v-else-if="breadcrumbs.length"
        :history="history"
        :selected-collections.sync="breadcrumbs"
        @viewCollection="drillDown" />

    <div v-else>
        <span class="sr-only">Loading...</span>
    </div>
</template>

<script>
import HistoryComponent from "./History";
import CurrentCollection from "./CurrentCollection/Panel";
import { History, STATES } from "./model";

export default {
    components: {
        HistoryComponent,
        CurrentCollection,
    },
    props: {
        history: { type: History, required: true },
    },
    data() {
        return {
            // list of collections we have drilled down into
            breadcrumbs: [],
        };
    },
    provide: {
        STATES,
    },
    methods: {
        drillDown(coll) {
            this.breadcrumbs = [...this.breadcrumbs, coll];
        },
    },
};
</script>
