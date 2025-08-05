<script setup lang="ts" generic="T extends Record<string, any>">
import { faArrowDown, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useInfiniteScroll } from "@vueuse/core";
import { BAlert, BListGroup } from "bootstrap-vue";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";
import { useAnimationFrameScroll } from "@/composables/sensors/animationFrameScroll";

import GButton from "@/components/BaseComponents/GButton.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ScrollToTopButton from "@/components/ToolsList/ScrollToTopButton.vue";

interface LoaderResult<T> {
    items: T[];
    total: number;
}

interface Props<T> {
    loader?: (offset: number, limit: number) => Promise<LoaderResult<T>>;
    loadDisabled?: boolean;
    limit?: number;
    itemKey: (item: T) => string | number;
    inPanel?: boolean;
    name?: string;
    namePlural?: string;
    propItems?: T[];
    propTotalCount?: number;
    propBusy?: boolean;
    /**
     * If true, the component will adjust the total item count based on changes in propItems.
     * This is useful when propItems can change independently of the loader.
     */
    adjustForTotalCountChanges?: boolean;
    /** The current scroll position of the list (used to track where the user has scrolled to). */
    propScrollTop?: number;
}

// TODO: In Vue 3, we'll be able to use generic types directly in the template, so we can remove this type assertion
// eslint-disable-next-line no-undef
const props = withDefaults(defineProps<Props<T>>(), {
    loader: undefined,
    loadDisabled: false,
    limit: 20,
    inPanel: false,
    name: "item",
    namePlural: "items",
    propItems: undefined,
    propTotalCount: undefined,
    propBusy: undefined,
    adjustForTotalCountChanges: false,
    propScrollTop: 0,
});

const emit = defineEmits<{
    (e: "load-more"): void;
    (e: "update:prop-scroll-top", value: number): void;
}>();

const scrollableDiv = ref<HTMLElement | null>(null);

// TODO: In Vue 3, we'll be able to use generic types directly in the template, so we can remove this type assertion
// eslint-disable-next-line no-undef
const localItems = ref<T[]>([]);

const localTotalItemCount = ref<number | undefined>(undefined);
const localBusy = ref(false);
const errorMessage = ref("");

// Computed properties, which check whether the props are provided or local state is to be used
const items = computed(() => (props.propItems !== undefined ? props.propItems : localItems.value));
const totalItemCount = computed(() => {
    // We are using local state entirely
    if (props.propTotalCount === undefined && props.propItems === undefined) {
        return localTotalItemCount.value;
    }

    const givenTotalCount: number | undefined =
        props.propTotalCount !== undefined ? props.propTotalCount : localTotalItemCount.value;

    // We are using a loader which means that the local state updates.
    // We also have prop items which might be more or less than local items (e.g.: store updates like new invocation/deleted history).
    // Note: We treat the prop items as the source of truth for the items to display.
    if (props.adjustForTotalCountChanges && props.propItems !== undefined && props.loader !== undefined) {
        // Here, we consider the case that prop items are updated via some external mechanism, and hence the total count might change
        // and then the given total count will not reflect that difference.
        return givenTotalCount !== undefined && props.propItems.length !== localItems.value.length
            ? Math.max(0, givenTotalCount + (props.propItems.length - localItems.value.length))
            : givenTotalCount;
    }

    return givenTotalCount;
});
const busy = computed(() => (props.propBusy !== undefined ? props.propBusy : localBusy.value));

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
    if (!busy.value && !allLoaded.value && !props.loadDisabled) {
        try {
            if (props.loader === undefined && props.propItems === undefined) {
                throw new Error("No loader function or propItems provided");
            }
            if (props.loader === undefined) {
                // If no loader is provided, we assume propItems is used
                emit("load-more");
                return;
            }

            localBusy.value = true;
            const offset = items.value.length;
            const { items: newItems, total } = await props.loader(offset, props.limit);
            // @ts-ignore - Vue 2.7 generic type compatibility issue, fix in Vue 3
            localItems.value = props.propItems ? props.propItems : localItems.value.concat(newItems);
            localTotalItemCount.value = total;
            errorMessage.value = "";
        } catch (e) {
            errorMessage.value = `Failed to load items: ${e}`;
        } finally {
            localBusy.value = false;
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

/** If `true`, we have a `props.scrollTop` with which the local `scrollTop` has been synced. */
const syncedWithPropScroll = ref(false);
watch(
    () => isScrollable.value,
    (scrollable: boolean) => {
        if (!scrollable && !allLoaded.value) {
            loadItems();
        }
        // If we were tracking where the list was scrolled to, return to that position
        if (props.propScrollTop !== undefined) {
            scrollableDiv.value?.scrollTo({ top: props.propScrollTop, behavior: "instant" });
            syncedWithPropScroll.value = true;
        }
    }
);
watch(
    () => scrollTop.value,
    (newScrollTop: number) => {
        // Once we have synced with the prop scroll, emit updates when the user scrolls to track the position
        if (syncedWithPropScroll.value) {
            emit("update:prop-scroll-top", newScrollTop);
        }
    }
);
</script>

<template>
    <div :class="inPanel ? 'unified-panel' : 'flex-column-overflow'">
        <slot name="search" />
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

                    <template v-if="!busy">
                        <slot v-if="allLoaded && items.length === 0" name="none-loaded-footer">
                            <div class="list-end">- No {{ props.namePlural }} found -</div>
                        </slot>

                        <slot v-else-if="allLoaded" name="all-loaded-footer">
                            <div class="list-end">- All {{ props.namePlural }} loaded -</div>
                        </slot>
                    </template>
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
                    v-if="!props.loadDisabled"
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

            <div class="ml-auto">
                <slot name="footer-button-area" />
            </div>
        </div>
    </div>
</template>
