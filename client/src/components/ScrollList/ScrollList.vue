<script setup lang="ts" generic="T extends Record<string, any>">
import { faArrowDown, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useInfiniteScroll } from "@vueuse/core";
import { BAlert, BListGroup } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";
import { useAnimationFrameScroll } from "@/composables/sensors/animationFrameScroll";

import GButton from "../BaseComponents/GButton.vue";
import LoadingSpan from "../LoadingSpan.vue";
import ScrollToTopButton from "@/components/ToolsList/ScrollToTopButton.vue";

interface LoaderResult<T> {
    items: T[];
    total: number;
}

interface Props<T> {
    loader: (offset: number, limit: number) => Promise<LoaderResult<T>>;
    limit?: number;
    itemKey: (item: T) => string | number;
    inPanel?: boolean;
    name?: string;
    namePlural?: string;
}

// TODO: In Vue 3, we'll be able to use generic types directly in the template, so we can remove this type assertion
// eslint-disable-next-line no-undef
const props = withDefaults(defineProps<Props<T>>(), {
    limit: 20,
    inPanel: false,
    name: "item",
    namePlural: "items",
});

// const emit = defineEmits(["item-clicked"]);

const scrollableDiv = ref<HTMLElement | null>(null);

// TODO: In Vue 3, we'll be able to use generic types directly in the template, so we can remove this type assertion
// eslint-disable-next-line no-undef
const items = ref<T[]>([]);

const totalItemCount = ref<number | undefined>(undefined);
const currentPage = ref(0);
const busy = ref(false);
const errorMessage = ref("");

// check if we have scrolled to the top or bottom of the scrollable div
const { arrived, scrollTop } = useAnimationFrameScroll(scrollableDiv);
const isScrollable = ref(false);
useAnimationFrameResizeObserver(scrollableDiv, ({ clientSize, scrollSize }) => {
    isScrollable.value = scrollSize.height >= clientSize.height + 1;
});
const scrolledTop = computed(() => !isScrollable.value || arrived.top);
const scrolledBottom = computed(() => !isScrollable.value || arrived.bottom);

const allLoaded = computed(() => totalItemCount.value !== undefined && totalItemCount.value <= items.value.length);

async function loadItems() {
    if (!busy.value && !allLoaded.value) {
        busy.value = true;
        try {
            const offset = props.limit * currentPage.value;
            const { items: newItems, total } = await props.loader(offset, props.limit);
            // @ts-ignore - Vue 2.7 generic type compatibility issue, fix in Vue 3
            items.value = items.value.concat(newItems);
            totalItemCount.value = total;
            currentPage.value += 1;
            errorMessage.value = "";
        } catch (e) {
            errorMessage.value = `Failed to load items: ${e}`;
        } finally {
            busy.value = false;
        }
    }
}

function scrollToTop() {
    scrollableDiv.value?.scrollTo({ top: 0, behavior: "smooth" });
}

onMounted(async () => {
    useInfiniteScroll(scrollableDiv.value, () => loadItems());
});

onUnmounted(() => {
    // Remove the infinite scrolling behavior
    useInfiniteScroll(scrollableDiv.value, () => {});
});

watch(
    () => isScrollable.value,
    (scrollable: boolean) => {
        if (!scrollable && !allLoaded.value) {
            loadItems();
        }
    }
);
</script>

<template>
    <div :class="inPanel ? 'unified-panel' : 'flex-column-overflow'">
        <div
            class="scroll-list-container flex-column-overflow"
            :class="{
                'in-panel': inPanel,
                'scrolled-top': scrolledTop,
                'scrolled-bottom': scrolledBottom,
            }">
            <div
                ref="scrollableDiv"
                class="scroll-list"
                :class="{
                    'in-panel': inPanel,
                    toolMenuContainer: inPanel,
                }"
                role="list">
                <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
                <BListGroup v-else>
                    <slot v-if="busy && items.length === 0" name="loading">
                        <BAlert variant="info" show>
                            <LoadingSpan :message="`Loading ${props.namePlural}`" />
                        </BAlert>
                    </slot>

                    <!-- Wrap slot in a template to use v-for -->
                    <div v-for="(item, index) in items" :key="itemKey(item)">
                        <slot name="item" :item="item" :index="index" />
                    </div>

                    <slot v-if="allLoaded && items.length === 0" name="none-loaded-footer">
                        <div class="text-center">No {{ props.namePlural }} found</div>
                    </slot>

                    <slot v-else-if="allLoaded" name="all-loaded-footer">
                        <div class="text-center">All {{ props.namePlural }} loaded</div>
                    </slot>
                </BListGroup>
            </div>
            <ScrollToTopButton :offset="scrollTop" @click="scrollToTop" />
        </div>
        <div :class="!inPanel && 'd-flex flex-row mt-3'">
            <div
                v-if="!allLoaded"
                class="mr-auto d-flex justify-content-center align-items-center"
                :class="inPanel && 'mt-1'">
                <i class="mr-1">Loaded {{ items.length }} out of {{ totalItemCount }} {{ props.namePlural }}</i>
                <GButton
                    data-description="load more items button"
                    size="small"
                    tooltip
                    :disabled="busy"
                    title="Load More"
                    transparent
                    @click="loadItems()">
                    <FontAwesomeIcon :icon="busy ? faSpinner : faArrowDown" :spin="busy" />
                </GButton>
            </div>
        </div>
    </div>
</template>
