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

type Item = { kind: "page"; key: string; page: number } | { kind: "ellipsis"; key: string };

// At this limit or below the window is a plain run of pages, with no ellipses
const ELLIPSIS_THRESHOLD = 3;

const rootRef = ref<HTMLElement | null>(null);
const internalPage = ref(1);

const safePerPage = computed(() => Math.max(Math.floor(props.perPage) || 20, 1));
// 0 shows one page button, a negative limit the default of 5
const safeLimit = computed(() => {
    const limit = Math.floor(props.limit) || 1;
    return limit < 1 ? 5 : limit;
});
const numberOfPages = computed(() => Math.max(Math.ceil(Math.max(props.totalRows || 0, 0) / safePerPage.value), 1));

const currentPage = computed(() => {
    const page = Math.floor(props.modelValue ?? internalPage.value) || 1;
    return Math.min(Math.max(page, 1), numberOfPages.value);
});

const items = computed<Item[]>(() => {
    const total = numberOfPages.value;
    const current = currentPage.value;
    const pages = (from: number, to: number): Item[] =>
        Array.from({ length: to - from + 1 }, (_, index) => ({
            kind: "page",
            key: `page-${from + index}`,
            page: from + index,
        }));
    const gap = (side: string): Item[] => (props.hideEllipsis ? [] : [{ kind: "ellipsis", key: `ellipsis-${side}` }]);

    const lead = props.firstNumber ? 1 : 0;
    const tail = props.lastNumber ? 1 : 0;
    const limit = safeLimit.value;

    if (limit <= ELLIPSIS_THRESHOLD) {
        if (total <= limit + lead + tail) {
            return pages(1, total);
        }
        // A pinned end inside the window frees its slot for one more page, keeping the item count
        let start = Math.min(Math.max(current - Math.floor(limit / 2), 1), total - limit + 1);
        let end = start + limit - 1;
        if (lead && start === 1) {
            end += 1;
        } else if (tail && end === total) {
            start -= 1;
        }
        return [
            ...(lead && start > 1 ? pages(1, 1) : []),
            ...pages(start, end),
            ...(tail && end < total ? pages(total, total) : []),
        ];
    }

    // Pages around the current one, plus one slot per ellipsis and pinned end: the item count stays
    // the same from page to page, so the buttons do not shift under the pointer.
    const middle = limit - 2;
    const slots = middle + 2 + lead + tail;
    if (total <= slots) {
        return pages(1, total);
    }

    const before = Math.floor((middle - 1) / 2);
    const start = current - before;
    const end = start + middle - 1;
    if (start <= lead + 2) {
        return [...pages(1, slots - 1 - tail), ...gap("end"), ...pages(total, total).slice(0, tail)];
    }
    if (end >= total - tail - 1) {
        return [...pages(1, 1).slice(0, lead), ...gap("start"), ...pages(total - (slots - 2 - lead), total)];
    }
    return [
        ...pages(1, 1).slice(0, lead),
        ...gap("start"),
        ...pages(start, end),
        ...gap("end"),
        ...pages(total, total).slice(0, tail),
    ];
});

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
    internalPage.value = page;
    emit("update:modelValue", page);
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
        const pageSizeChanged = perPage !== oldPerPage && rows === oldRows;
        const requested = Math.floor(props.modelValue ?? internalPage.value) || 1;
        const pagesShrankPastCurrent = pages !== oldPages && requested > pages;
        if ((pageSizeChanged || pagesShrankPastCurrent) && requested !== 1) {
            internalPage.value = 1;
            emit("update:modelValue", 1);
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
    gap: var(--spacing-1);
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
