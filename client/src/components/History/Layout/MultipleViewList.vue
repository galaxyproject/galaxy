<template>
    <virtual-list
        v-if="filteredHistories.length"
        :keeps="10"
        :estimate-size="histories.length"
        :data-key="'id'"
        :data-component="MultipleViewItem"
        :data-sources="filteredHistories"
        :direction="'horizontal'"
        :extra-props="{ currentHistoryId, handlers, dataSetsFilter, onViewCollection }"
        :item-style="{ minWidth: '15rem', maxWidth: '15rem' }"
        item-class="d-flex mx-1"
        class="flex-grow-1"
        style="overflow: auto hidden"
        wrap-class="row container flex-nowrap h-100 m-0">
    </virtual-list>
    <b-alert v-else class="m-2" variant="info" show>
        <span v-if="historiesFilter" class="font-weight-bold">No History found with this filter.</span>
        <span v-else class="font-weight-bold">No History found.</span>
    </b-alert>
</template>

<script>
import VirtualList from "vue-virtual-scroll-list";
import MultipleViewItem from "./MultipleViewItem";

export default {
    components: {
        VirtualList,
    },
    props: {
        histories: {
            type: Array,
            required: true,
        },
        currentHistoryId: {
            type: String,
            required: true,
        },
        handlers: {
            type: Object,
            required: true,
        },
        historiesFilter: {
            type: String,
            default: "",
        },
        dataSetsFilter: {
            type: String,
            default: "",
        },
    },
    data() {
        return { MultipleViewItem };
    },
    computed: {
        filteredHistories() {
            if (!this.historiesFilter) {
                return this.histories;
            }
            const filter = this.historiesFilter.toLowerCase();
            return this.histories?.filter((history) => {
                return history.name.toLowerCase().includes(filter);
            });
        },
    },
    methods: {
        onViewCollection(collection) {},
    },
};
</script>
