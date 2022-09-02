<template>
    <div class="list-container d-flex h-100 w-auto overflow-auto">
        <virtual-list
            v-if="selectedHistories.length"
            :keeps="10"
            :estimate-size="histories.length"
            :data-key="'id'"
            :data-component="MultipleViewItem"
            :data-sources="selectedHistories"
            :direction="'horizontal'"
            :extra-props="{ currentHistory, handlers, filter, removeHistoryFromList }"
            :item-style="{ width: '15rem' }"
            item-class="d-flex mx-1 mt-1"
            class="d-flex"
            wrap-class="row flex-nowrap m-0">
        </virtual-list>

        <div
            v-b-modal.select-histories-modal
            class="history-picker text-primary d-flex m-3 p-5 align-items-center text-nowrap">
            Select histories
        </div>

        <SelectorModal
            id="select-histories-modal"
            :multiple="true"
            :histories="histories"
            :current-history-id="currentHistory.id"
            title="Select histories"
            @selectHistories="addHistoriesToList" />
    </div>
</template>

<script>
import VirtualList from "vue-virtual-scroll-list";
import MultipleViewItem from "./MultipleViewItem";
import SelectorModal from "components/History/Modals/SelectorModal";

export default {
    components: {
        VirtualList,
        SelectorModal,
    },
    props: {
        histories: {
            type: Array,
            required: true,
        },
        currentHistory: {
            type: Object,
            required: true,
        },
        handlers: {
            type: Object,
            required: true,
        },
        filter: {
            type: String,
            default: "",
        },
    },
    data() {
        return {
            MultipleViewItem,
            selectedHistories: [],
        };
    },
    created() {
        this.selectedHistories = [this.histories[0]];
    },
    methods: {
        addHistoriesToList(histories) {
            histories.forEach((history) => {
                if (!this.selectedHistories.includes(history)) {
                    this.selectedHistories.push(history);
                }
            });
        },
        removeHistoryFromList(history) {
            this.selectedHistories = this.selectedHistories.filter((item) => {
                return item.id !== history.id;
            });
        },
    },
};
</script>

<style lang="scss">
.list-container {
    width: fit-content;

    .history-picker {
        border: dotted lightgray;
    }
}
</style>
