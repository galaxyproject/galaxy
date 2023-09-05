<script setup lang="ts">
import { computed, type Ref, ref } from "vue";
//@ts-ignore missing typedefs
import VirtualList from "vue-virtual-scroll-list";

import { copyDataset } from "@/components/Dataset/services";
import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";
import { useAnimationFrameScroll } from "@/composables/sensors/animationFrameScroll";
import { Toast } from "@/composables/toast";
import type { HistorySummary } from "@/stores/historyStore";
import { useHistoryStore } from "@/stores/historyStore";

import MultipleViewItem from "./MultipleViewItem.vue";

const historyStore = useHistoryStore();

const props = withDefaults(
    defineProps<{
        histories: HistorySummary[];
        selectedHistories: { id: string }[];
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
const pickerClass = computed(
    () =>
        "history-picker text-primary d-flex m-3 p-5 align-items-center text-nowrap" +
        (showDropZone.value ? " item-drop-effect" : "")
);

const showDropZone = ref(false);
const processingDrop = ref(false);
function onDragEnter(evt: MouseEvent) {
    showDropZone.value = true;
}

function onDragLeave(evt: MouseEvent) {
    showDropZone.value = false;
}
async function onDrop(evt: any) {
    if (processingDrop.value) {
        return;
    }
    showDropZone.value = false;
    processingDrop.value = true;
    let data: any;
    try {
        data = JSON.parse(evt.dataTransfer.getData("text"))[0];
    } catch (error) {
        // this was not a valid object for this dropzone, ignore
    }
    if (data) {
        await historyStore.createNewHistory();
        const currentHistoryId = historyStore.currentHistoryId;
        const dataSource = data.history_content_type === "dataset" ? "hda" : "hdca";
        if (currentHistoryId) {
            await copyDataset(data.id, currentHistoryId, data.history_content_type, dataSource)
                .then(() => {
                    if (data.history_content_type === "dataset") {
                        Toast.info("Dataset copied to history");
                    } else {
                        Toast.info("Collection copied to history");
                    }
                    historyStore.loadHistoryById(currentHistoryId);
                })
                .catch((error) => {
                    Toast.error(error);
                });
            historyStore.pinHistory(currentHistoryId);
        }
        processingDrop.value = false;
    }
}
</script>

<template>
    <div class="list-container h-100" :class="{ 'scrolled-left': scrolledLeft, 'scrolled-right': scrolledRight }">
        <div ref="scrollContainer" class="d-flex h-100 w-auto overflow-auto">
            <VirtualList
                v-if="props.selectedHistories.length"
                :estimate-size="props.selectedHistories.length"
                :data-key="'id'"
                :data-component="MultipleViewItem"
                :data-sources="props.selectedHistories"
                :direction="'horizontal'"
                :extra-props="{ filter }"
                :item-style="{ width: '15rem' }"
                item-class="d-flex mx-1 mt-1"
                class="d-flex"
                wrap-class="row flex-nowrap m-0">
            </VirtualList>

            <div
                :class="pickerClass"
                @click.stop="$emit('update:show-modal', true)"
                @drop.prevent="onDrop"
                @dragenter.prevent="onDragEnter"
                @dragover.prevent
                @dragleave.prevent="onDragLeave">
                Select histories
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.list-container {
    .history-picker {
        border: dotted lightgray;
        cursor: pointer;
    }

    .item-drop-effect {
        border: lightgray;
        background-color: gainsboro;
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
