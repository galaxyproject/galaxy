<script setup lang="ts">
/**
 * Page navigation for a list split into pages of `perPage` rows: a `<nav>` landmark holding a list
 * of page buttons, previous/next buttons and optional first/last buttons.
 *
 * `v-model` is the 1-based current page. A user click emits `update:modelValue` and `change` with
 * the new page; `change` fires only for clicks. Without a bound `modelValue` the pager keeps its own
 * page. When the page count drops below the current page, or the page size changes, it goes back to
 * page 1 and emits `update:modelValue` (not `change`).
 *
 * Attributes such as `class` and `data-description` land on the `<nav>`.
 */

import { computed, nextTick, ref, watch } from "vue";

import { pageWindow } from "../utils/pageWindow";
import { type ComponentSize, prefix } from "./componentVariants";

defineOptions({
    // Under @vue/compat, keep v-model on modelValue instead of Vue 2's value/input
    compatConfig: { COMPONENT_V_MODEL: false },
});

type ItemClass = string | string[] | Record<string, boolean>;

interface Props {
    /** The v-model value: the current page, starting at 1 */
    modelValue?: number;
    /** Total number of rows across all pages */
    totalRows?: number;
    /** Rows per page */
    perPage?: number;
    /** Page number buttons to show in the window, not counting pinned first/last numbers; 3 or less shows no ellipses */
    limit?: number;
    /** Horizontal placement of the buttons */
    align?: "left" | "center" | "right";
    /** Displayed size of the buttons */
    size?: ComponentSize;
    /** Disables every button */
    disabled?: boolean;
    /** Always show page 1, in place of the go-to-first button */
    firstNumber?: boolean;
    /** Always show the last page, in place of the go-to-last button */
    lastNumber?: boolean;
    /** Hide the go-to-first and go-to-last buttons */
    hideGotoEndButtons?: boolean;
    /** Hide the ellipses that stand for skipped pages */
    hideEllipsis?: boolean;
    /** Accessible name of the navigation landmark */
    ariaLabel?: string;
    /** ID of the element the pager controls, set as aria-controls on every button */
    ariaControls?: string;
    firstText?: string;
    prevText?: string;
    nextText?: string;
    lastText?: string;
    ellipsisText?: string;
    labelFirstPage?: string;
    labelPrevPage?: string;
    labelNextPage?: string;
    labelLastPage?: string;
    /** Page button label: a prefix followed by the page number, or a function of the page */
    labelPage?: string | ((page: number) => string);
    /** Extra classes for the list items of page buttons */
    pageClass?: ItemClass;
    firstClass?: ItemClass;
    prevClass?: ItemClass;
    nextClass?: ItemClass;
    lastClass?: ItemClass;
    ellipsisClass?: ItemClass;
}

const props = withDefaults(defineProps<Props>(), {
    modelValue: undefined,
    totalRows: 0,
    perPage: 20,
    limit: 5,
    align: "left",
    size: "medium",
    ariaLabel: "Pagination",
    ariaControls: undefined,
    firstText: "«",
    prevText: "‹",
    nextText: "›",
    lastText: "»",
    ellipsisText: "…",
    labelFirstPage: "Go to first page",
    labelPrevPage: "Go to previous page",
    labelNextPage: "Go to next page",
    labelLastPage: "Go to last page",
    labelPage: "Go to page",
    pageClass: undefined,
    firstClass: undefined,
    prevClass: undefined,
    nextClass: undefined,
    lastClass: undefined,
    ellipsisClass: undefined,
});

const emit = defineEmits<{
    (e: "update:modelValue", page: number): void;
    (e: "change", page: number): void;
}>();

const rootRef = ref<HTMLElement | null>(null);
const internalPage = ref(1);

const atLeastOne = (value: number) => Math.max(Math.floor(value) || 1, 1);

const safePerPage = computed(() => atLeastOne(props.perPage));
const safeLimit = computed(() => atLeastOne(props.limit));
const numberOfPages = computed(() => Math.max(Math.ceil(Math.max(props.totalRows || 0, 0) / safePerPage.value), 1));

// The bound page if there is one, else the pager's own; setting it emits update:modelValue
const requestedPage = computed({
    get: () => Math.floor(props.modelValue ?? internalPage.value) || 1,
    set: (page: number) => {
        internalPage.value = page;
        emit("update:modelValue", page);
    },
});
const currentPage = computed(() => Math.min(Math.max(requestedPage.value, 1), numberOfPages.value));

const items = computed(() =>
    pageWindow({
        total: numberOfPages.value,
        current: currentPage.value,
        limit: safeLimit.value,
        firstNumber: props.firstNumber,
        lastNumber: props.lastNumber,
        hideEllipsis: props.hideEllipsis,
    }),
);

const showFirstButton = computed(() => !props.hideGotoEndButtons && !props.firstNumber);
const showLastButton = computed(() => !props.hideGotoEndButtons && !props.lastNumber);
const atFirst = computed(() => currentPage.value <= 1);
const atLast = computed(() => currentPage.value >= numberOfPages.value);

function pageLabel(page: number) {
    return typeof props.labelPage === "function" ? props.labelPage(page) : `${props.labelPage} ${page}`;
}

const rootClasses = computed(() => [prefix(props.size), `g-align-${props.align}`]);

let clickedButton: HTMLButtonElement | null = null;

function goTo(page: number, event: MouseEvent) {
    if (props.disabled || page === currentPage.value) {
        return;
    }
    clickedButton = event.currentTarget as HTMLButtonElement;
    requestedPage.value = page;
    emit("change", page);
}

// A clicked next/last button can turn disabled, or a page button drop out of the window, which
// would leave keyboard focus on nothing.
watch(
    currentPage,
    async () => {
        const button = clickedButton;
        clickedButton = null;
        const active = document.activeElement;
        const focusLost = !active || active === document.body || active === button;
        if (button && focusLost && (button.disabled || !button.isConnected)) {
            await nextTick();
            rootRef.value?.querySelector<HTMLButtonElement>('button[aria-current="page"]')?.focus();
        }
    },
    { flush: "post" },
);

watch(
    () => [safePerPage.value, numberOfPages.value, props.totalRows] as const,
    ([perPage, pages, rows], [oldPerPage, oldPages, oldRows]) => {
        // A page size changing along with the row count means new results: the page stays unless it is gone
        const pageSizeChanged = perPage !== oldPerPage && rows === oldRows;
        const pagesShrankPastCurrent = pages !== oldPages && requestedPage.value > pages;
        if ((pageSizeChanged || pagesShrankPastCurrent) && requestedPage.value !== 1) {
            requestedPage.value = 1;
        }
    },
);
</script>

<template>
    <nav ref="rootRef" class="g-pagination" :class="rootClasses" :aria-label="props.ariaLabel">
        <ul class="g-pagination-list">
            <li v-if="showFirstButton" class="g-pagination-item" :class="props.firstClass">
                <button
                    type="button"
                    class="g-pagination-button"
                    :disabled="props.disabled || atFirst"
                    :aria-label="props.labelFirstPage"
                    :aria-controls="props.ariaControls"
                    @click="goTo(1, $event)">
                    <span aria-hidden="true">{{ props.firstText }}</span>
                </button>
            </li>
            <li class="g-pagination-item" :class="props.prevClass">
                <button
                    type="button"
                    class="g-pagination-button"
                    :disabled="props.disabled || atFirst"
                    :aria-label="props.labelPrevPage"
                    :aria-controls="props.ariaControls"
                    @click="goTo(currentPage - 1, $event)">
                    <span aria-hidden="true">{{ props.prevText }}</span>
                </button>
            </li>
            <template v-for="item in items" :key="item.key">
                <li v-if="item.kind === 'page'" class="g-pagination-item" :class="props.pageClass">
                    <button
                        type="button"
                        class="g-pagination-button"
                        :disabled="props.disabled"
                        :data-page="item.page"
                        :aria-label="pageLabel(item.page)"
                        :aria-current="item.page === currentPage ? 'page' : undefined"
                        :aria-controls="props.ariaControls"
                        @click="goTo(item.page, $event)">
                        {{ item.page }}
                    </button>
                </li>
                <li
                    v-else
                    class="g-pagination-item g-pagination-ellipsis"
                    :class="props.ellipsisClass"
                    aria-hidden="true">
                    <span>{{ props.ellipsisText }}</span>
                </li>
            </template>
            <li class="g-pagination-item" :class="props.nextClass">
                <button
                    type="button"
                    class="g-pagination-button"
                    :disabled="props.disabled || atLast"
                    :aria-label="props.labelNextPage"
                    :aria-controls="props.ariaControls"
                    @click="goTo(currentPage + 1, $event)">
                    <span aria-hidden="true">{{ props.nextText }}</span>
                </button>
            </li>
            <li v-if="showLastButton" class="g-pagination-item" :class="props.lastClass">
                <button
                    type="button"
                    class="g-pagination-button"
                    :disabled="props.disabled || atLast"
                    :aria-label="props.labelLastPage"
                    :aria-controls="props.ariaControls"
                    @click="goTo(numberOfPages, $event)">
                    <span aria-hidden="true">{{ props.lastText }}</span>
                </button>
            </li>
        </ul>
    </nav>
</template>

<style scoped lang="scss">
// Zero specificity, so a margin utility class on the component wins
:where(.g-pagination) {
    margin-bottom: var(--spacing-4);
}

.g-pagination {
    display: flex;

    &.g-align-center {
        justify-content: center;
    }

    &.g-align-right {
        justify-content: flex-end;
    }
}

.g-pagination-list {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-2);
    margin: 0;
    padding: 0;
    list-style: none;
}

.g-pagination-item {
    display: flex;
}

.g-pagination-button,
.g-pagination-ellipsis span {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2.25em;
    padding: var(--spacing-1) var(--spacing-2);
    border: 1px solid transparent;
    border-radius: var(--spacing-1);
    line-height: 1.5;
}

.g-pagination-button {
    margin: 0;
    // grey-400 keeps the button outline at 3:1 against the page
    border-color: var(--color-grey-400);
    background-color: var(--background-color);
    color: var(--color-blue-600);
    font: inherit;
    cursor: pointer;
    transition:
        color 0.15s ease-in-out,
        background-color 0.15s ease-in-out,
        border-color 0.15s ease-in-out;

    @media (prefers-reduced-motion) {
        transition: none;
    }

    // The current page keeps its fill: blue-100 text on grey-200 would drop to 1.22:1
    &:hover:not(:disabled):not([aria-current="page"]) {
        background-color: var(--color-grey-200);
    }

    &:focus {
        outline: none;
    }

    // Page-background gap keeps the ring clear of the filled current page; outline survives forced colors.
    &:focus-visible {
        position: relative;
        z-index: 1;
        outline: 2px solid var(--color-blue-600);
        outline-offset: 2px;
        box-shadow: 0 0 0 2px var(--background-color);
    }

    &:disabled {
        border-color: var(--color-grey-200);
        background-color: var(--color-grey-100);
        color: var(--color-grey-500);
        cursor: default;
    }

    // After :disabled, so a disabled pager still marks its current page
    &[aria-current="page"] {
        border-color: var(--color-blue-600);
        background-color: var(--color-blue-600);
        color: var(--color-blue-100);
        cursor: default;
    }
}

.g-pagination-ellipsis span {
    color: var(--color-grey-600);
}

.g-small {
    font-size: var(--font-size-small);
}

.g-medium {
    font-size: var(--font-size-medium);
}

.g-large {
    font-size: var(--font-size-large);

    .g-pagination-button,
    .g-pagination-ellipsis span {
        padding: var(--spacing-2) var(--spacing-3);
    }
}
</style>
