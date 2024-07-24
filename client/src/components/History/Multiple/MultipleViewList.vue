<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckSquare, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, type Ref, ref } from "vue";
//@ts-ignore missing typedefs
import VirtualList from "vue-virtual-scroll-list";

import { type HistoryItemSummary, isHistoryItem } from "@/api";
import { copyDataset } from "@/api/datasets";
import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";
import { useAnimationFrameScroll } from "@/composables/sensors/animationFrameScroll";
import { Toast } from "@/composables/toast";
import { useEventStore } from "@/stores/eventStore";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import HistoryDropZone from "../CurrentHistory/HistoryDropZone.vue";
import MultipleViewItem from "./MultipleViewItem.vue";

library.add(faCheckSquare, faPlus);

const historyStore = useHistoryStore();

const props = withDefaults(
    defineProps<{
        selectedHistories: { id: string }[];
        filter?: string;
    }>(),
    {
        filter: "",
    }
);

// defineEmits below
const emit = defineEmits<{
    (e: "update:show-modal", value: boolean): void;
}>();

const scrollContainer: Ref<HTMLElement | null> = ref(null);
const { arrived } = useAnimationFrameScroll(scrollContainer);

const isScrollable = ref(false);
useAnimationFrameResizeObserver(scrollContainer, ({ clientSize, scrollSize }) => {
    isScrollable.value = scrollSize.width >= clientSize.width + 1;
});

const scrolledLeft = computed(() => !isScrollable.value || arrived.left);
const scrolledRight = computed(() => !isScrollable.value || arrived.right);

async function createAndPin() {
    try {
        await historyStore.createNewHistory();
        if (!historyStore.currentHistoryId) {
            throw new Error("Error creating history");
        }

        if (historyStore.pinnedHistories.length > 0) {
            historyStore.pinHistory(historyStore.currentHistoryId);
        }
    } catch (error: any) {
        console.error(error);
        Toast.error(errorMessageAsString(error), "Error creating and pinning history");
    }
}

const showDropZone = ref(false);
const processingDrop = ref(false);
async function onDrop(evt: any) {
    const eventStore = useEventStore();
    if (processingDrop.value) {
        showDropZone.value = false;
        return;
    }
    processingDrop.value = true;
    showDropZone.value = false;
    const dragItems = eventStore.getDragItems();
    // Filter out any non-history items
    const historyItems = dragItems?.filter((item: any) => isHistoryItem(item)) as HistoryItemSummary[];
    const multiple = historyItems.length > 1;
    const originalHistoryId = historyItems?.[0]?.history_id;

    if (historyItems && originalHistoryId) {
        await historyStore.createNewHistory();
        const currentHistoryId = historyStore.currentHistoryId;

        let datasetCount = 0;
        let collectionCount = 0;
        if (currentHistoryId) {
            // iterate over the data array and copy each item to the new history
            for (const item of historyItems) {
                const dataSource = item.history_content_type === "dataset" ? "hda" : "hdca";
                await copyDataset(item.id, currentHistoryId, item.history_content_type, dataSource)
                    .then(() => {
                        if (item.history_content_type === "dataset") {
                            datasetCount++;
                            if (!multiple) {
                                Toast.info(localize("Dataset copied to new history"));
                            }
                        } else {
                            collectionCount++;
                            if (!multiple) {
                                Toast.info(localize("Collection copied to new history"));
                            }
                        }
                    })
                    .catch((error) => {
                        Toast.error(errorMessageAsString(error));
                    });
            }
            if (multiple && datasetCount > 0) {
                Toast.info(`${datasetCount} dataset${datasetCount > 1 ? "s" : ""} copied to new history`);
            }
            if (multiple && collectionCount > 0) {
                Toast.info(`${collectionCount} collection${collectionCount > 1 ? "s" : ""} copied to new history`);
            }

            if (historyStore.pinnedHistories.length > 0) {
                // pin the newly created history via the drop
                historyStore.pinHistory(currentHistoryId);
                // also pin the original history where the item came from
                historyStore.pinHistory(originalHistoryId);
            }
        }
        processingDrop.value = false;
    }
}

async function onKeyDown(evt: KeyboardEvent) {
    if (evt.key === "Enter" || evt.key === " ") {
        if ((evt.target as HTMLElement)?.classList?.contains("top-picker")) {
            await createAndPin();
        } else if ((evt.target as HTMLElement)?.classList?.contains("bottom-picker")) {
            emit("update:show-modal", true);
        }
    }
}
</script>

<template>
    <!-- eslint-disable vuejs-accessibility/no-static-element-interactions -->
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
                :item-style="{ width: '100%', minWidth: '15rem' }"
                item-class="d-flex mx-1 mt-1"
                class="d-flex"
                wrap-class="row flex-nowrap m-0">
            </VirtualList>

            <div
                class="history-picker"
                @drop.prevent="onDrop"
                @dragenter.prevent="showDropZone = true"
                @dragover.prevent
                @dragleave.prevent="showDropZone = false">
                <span v-if="!showDropZone" class="d-flex flex-column h-100">
                    <div
                        class="history-picker-box top-picker text-primary"
                        tabindex="0"
                        @keydown="onKeyDown"
                        @click.stop="createAndPin">
                        <FontAwesomeIcon :icon="faPlus" class="mr-1" />
                        {{ localize("Create and pin new history") }}
                    </div>
                    <div
                        class="history-picker-box bottom-picker text-primary"
                        tabindex="0"
                        @keydown="onKeyDown"
                        @click.stop="emit('update:show-modal', true)">
                        <FontAwesomeIcon :icon="faCheckSquare" class="mr-1" />
                        {{ localize("Select histories") }}
                    </div>
                </span>
                <div v-else class="history-picker-box history-picker-drop-zone text-primary">
                    {{ localize("Create new history with this item") }}
                    <HistoryDropZone />
                </div>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";
.list-container {
    .history-picker {
        min-width: 15rem;
        max-width: 15rem;
        margin: 1rem;
        .history-picker-box {
            border: dotted lightgray;
            cursor: pointer;
            position: relative;
            justify-content: center;
            display: flex;
            align-items: center;
            text-wrap: none;
            &.top-picker {
                height: 20%;
            }
            &.bottom-picker {
                height: 80%;
            }
            &:not(.history-picker-drop-zone) {
                &:hover {
                    background-color: rgba($brand-info, 0.2);
                }
            }
            &.history-picker-drop-zone {
                height: 100%;
            }
        }
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
