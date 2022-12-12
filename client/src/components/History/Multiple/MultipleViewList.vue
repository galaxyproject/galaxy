<template>
    <div class="list-container h-100" :class="{ 'scrolled-left': scrolledLeft, 'scrolled-right': scrolledRight }">
        <div ref="scrollContainer" class="d-flex h-100 w-auto overflow-auto">
            <virtual-list
                v-if="selectedHistories.length"
                :estimate-size="selectedHistories.length"
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
    </div>
</template>

<script>
import { mapActions, mapState } from "pinia";
import VirtualList from "vue-virtual-scroll-list";
import MultipleViewItem from "./MultipleViewItem";
import { useHistoryStore } from "stores/historyStore";
import SelectorModal from "components/History/Modals/SelectorModal";
import { useAnimationFrameScroll } from "composables/sensors/animationFrameScroll";
import { useAnimationFrameResizeObserver } from "composables/sensors/animationFrameResizeObserver";
import { computed, ref } from "vue";

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
    setup() {
        const scrollContainer = ref(null);
        const isScrollable = ref(false);
        const { arrived } = useAnimationFrameScroll(scrollContainer);

        useAnimationFrameResizeObserver(scrollContainer, ({ clientSize, scrollSize }) => {
            isScrollable.value = scrollSize.width >= clientSize.width + 1;
        });

        const scrolledLeft = computed(() => !isScrollable.value || arrived.left);
        const scrolledRight = computed(() => !isScrollable.value || arrived.right);

        return {
            scrollContainer,
            scrolledLeft,
            scrolledRight,
        };
    },
    data() {
        return {
            MultipleViewItem,
        };
    },
    computed: {
        ...mapState(useHistoryStore, ["pinnedHistories"]),
        selectedHistories() {
            return this.pinnedHistories;
        },
    },
    created() {
        if (!this.selectedHistories.length) {
            const firstHistory = this.histories[0];
            this.pinHistory(firstHistory.id);
        }
    },
    methods: {
        ...mapActions(useHistoryStore, ["pinHistory", "unpinHistory"]),
        addHistoriesToList(histories) {
            histories.forEach((history) => {
                const historyExists = this.selectedHistories.find((h) => h.id == history.id);
                if (!historyExists) {
                    this.pinHistory(history.id);
                }
            });
        },
        removeHistoryFromList(history) {
            this.unpinHistory(history.id);
        },
    },
};
</script>

<style lang="scss" scoped>
.list-container {
    .history-picker {
        border: dotted lightgray;
    }

    position: relative;

    &:before,
    &:after {
        position: absolute;
        content: "";
        pointer-events: none;
        z-index: 10;
        width: 20px;
        height: 100%;
        top: 0;
        opacity: 0;

        background-repeat: no-repeat;
        transition: opacity 0.4s;
    }

    &:before {
        left: 0;
        background-image: linear-gradient(to right, rgba(3, 0, 48, 0.1), rgba(3, 0, 48, 0.02), rgba(3, 0, 48, 0));
    }

    &:not(.scrolled-left) {
        &:before {
            opacity: 1;
        }
    }

    &:after {
        right: 0;
        background-image: linear-gradient(to left, rgba(3, 0, 48, 0.1), rgba(3, 0, 48, 0.02), rgba(3, 0, 48, 0));
    }

    &:not(.scrolled-right) {
        &:after {
            opacity: 1;
        }
    }
}
</style>
