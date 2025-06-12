<script lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArrowDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useInfiniteScroll } from "@vueuse/core";
import { BAlert } from "bootstrap-vue";
import type { PropType } from "vue";
import { computed, defineComponent, onMounted, onUnmounted, ref, watch } from "vue";

import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";
import { useAnimationFrameScroll } from "@/composables/sensors/animationFrameScroll";

import ScrollToTopButton from "@/components/ToolsList/ScrollToTopButton.vue";

library.add(faArrowDown);

interface LoaderResult<T> {
    items: T[];
    total: number;
}

export default defineComponent({
    name: "ScrollList",
    components: {
        FontAwesomeIcon,
        ScrollToTopButton,
    },
    props: {
        loader: {
            type: Function as PropType<(offset: number, limit: number) => Promise<LoaderResult<any>>>, // we'll override `any` later
            required: true,
        },
        limit: {
            type: Number,
            default: 20,
        },
        itemKey: {
            type: Function as PropType<(item: any) => string | number>, // override later
            required: true,
        },
        inPanel: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["item-clicked"],
    setup(props, { emit }) {
        const scrollableDiv = ref<HTMLElement | null>(null);
        const items = ref<unknown[]>([]);
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

        const allLoaded = computed(
            () => totalItemCount.value !== undefined && totalItemCount.value <= items.value.length
        );

        async function loadItems() {
            if (!busy.value && !allLoaded.value) {
                busy.value = true;
                try {
                    const offset = props.limit * currentPage.value;
                    const { items: newItems, total } = await props.loader(offset, props.limit);
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

        return {
            scrollableDiv,
            items,
            allLoaded,
            busy,
            errorMessage,
            loadItems,
            totalItemCount,
            BAlert,
            faArrowDown,
            scrolledTop,
            scrolledBottom,
            scrollTop,
            scrollToTop,
        };
    },
});
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
                    <slot v-if="busy && items.length === 0" name="loading" />

                    <!-- Wrap slot in a template to use v-for -->
                    <div v-for="(item, index) in items" :key="itemKey(item)">
                        <slot name="item" :item="item" :index="index" />
                    </div>

                    <slot v-if="allLoaded" name="footer" />
                </BListGroup>
            </div>
            <ScrollToTopButton :offset="scrollTop" @click="scrollToTop" />
        </div>
        <div :class="!inPanel && 'd-flex flex-row mt-3'">
            <div
                v-if="!allLoaded"
                class="mr-auto d-flex justify-content-center align-items-center"
                :class="inPanel && 'mt-1'">
                <i class="mr-1">Loaded {{ items.length }} out of {{ totalItemCount }} invocations</i>
                <BButton
                    v-b-tooltip.noninteractive.hover
                    data-description="load more invocations button"
                    size="sm"
                    title="Load More"
                    variant="link"
                    @click="loadItems()">
                    <FontAwesomeIcon :icon="faArrowDown" />
                </BButton>
            </div>
        </div>
    </div>
</template>
