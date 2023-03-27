<script setup lang="ts">
import { computed, ref, type Ref } from "vue";
//@ts-ignore missing typedefs
import VirtualList from "vue-virtual-scroll-list";
import MultipleViewItem from "./MultipleViewItem.vue";
import { useHistoryStore } from "@/stores/historyStore";
import SelectorModal from "@/components/History/Modals/SelectorModal.vue";
import { useAnimationFrameScroll } from "@/composables/sensors/animationFrameScroll";
import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";

const historyStore = useHistoryStore();

interface History {
    id: string;
}

const props = withDefaults(
    defineProps<{
        histories: History[];
        currentHistory: History;
        // todo: stricter typedef for handlers, when MultipleViewItem is refactored
        handlers: { [handler: string]: Function };
        filter?: string;
    }>(),
    {
        filter: "",
    }
);

const scrollContainer: Ref<HTMLElement | null> = ref(null);
const { arrived } = useAnimationFrameScroll(scrollContainer);

const isScrollable = ref(false);
useAnimationFrameResizeObserver(scrollContainer, ({ clientSize, scrollSize }) => {
    isScrollable.value = scrollSize.width >= clientSize.width + 1;
});

const scrolledLeft = computed(() => !isScrollable.value || arrived.left);
const scrolledRight = computed(() => !isScrollable.value || arrived.right);

const selectedHistories: Ref<History[]> = computed(() => historyStore.pinnedHistories);

function removeHistoryFromList(history: History) {
    historyStore.unpinHistory(history.id);
}

if (!selectedHistories.value.length ?? props.histories.length > 0) {
    historyStore.pinHistory(props.histories[0]!.id);
}

function addHistoriesToList(histories: History[]) {
    histories.forEach((history) => {
        const historyExists = selectedHistories.value.find((h) => h.id === history.id);
        if (!historyExists) {
            historyStore.pinHistory(history.id);
        }
    });
}
</script>

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
