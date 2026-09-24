<script setup lang="ts">
/**
 * Popover component using @floating-ui/dom for positioning.
 * Replaces BPopover from bootstrap-vue.
 *
 * NOTE: Uses Bootstrap CSS class names (popover, b-popover, popover-header, popover-body)
 * for styling compatibility. Replace with custom g-popover styles when dropping Bootstrap CSS.
 *
 * Supports:
 * - String target (element ID) or HTMLElement ref
 * - Trigger modes: hover, click, manual
 * - Placement with flip/shift
 * - Title via prop or #title slot
 * - Content via prop or default slot
 * - Programmatic show/hide via v-model (:show.sync)
 * - boundary prop (currently always uses window via altBoundary)
 * - custom-class prop
 */

import { arrow, type ComputePositionConfig, flip, offset, type Placement, shift } from "@floating-ui/dom";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { useFloatingPosition } from "../composables/floatingPosition";

type TriggerType = "hover" | "click" | "click blur" | "hover focus" | "manual" | "manual hover" | "focus";

const props = withDefaults(
    defineProps<{
        /**
         * Element ID string, Element ref, or function returning an element to anchor the popover to.
         * Function return type is intentionally broad (any) to match BPopover's behavior — callers
         * may pass `() => $refs.x` which can return a Vue component instance; resolveTarget handles
         * unwrapping via .$el.
         */
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        target?: string | Element | (() => any);
        /** Trigger mode(s) */
        triggers?: TriggerType;
        /** Placement relative to target */
        placement?: string;
        /** Boundary for positioning (currently just flags altBoundary) */
        boundary?: string;
        /** Title text (or use #title slot) */
        title?: string;
        /** Content text (or use default slot) */
        content?: string;
        /** Programmatic show/hide (v-model via :show.sync) */
        show?: boolean;
        /** Custom CSS class on the popover element */
        customClass?: string;
    }>(),
    {
        target: undefined,
        triggers: "hover",
        placement: "auto",
        boundary: undefined,
        title: undefined,
        content: undefined,
        show: undefined,
        customClass: undefined,
    },
);

const emit = defineEmits<{
    (e: "update:show", value: boolean): void;
    (e: "shown"): void;
    (e: "hidden"): void;
}>();

const popoverEl = ref<HTMLDivElement>();
const arrowEl = ref<HTMLDivElement>();
const isVisible = ref(false);

// Two-way binding: if show prop is provided, use it; otherwise manage internally
const showState = computed({
    get: () => (props.show !== undefined ? props.show : isVisible.value),
    set: (val: boolean) => {
        isVisible.value = val;
        if (props.show !== undefined) {
            emit("update:show", val);
        }
    },
});

function resolveTarget(): Element | null {
    if (!props.target) {
        return null;
    }
    if (typeof props.target === "function") {
        const result = props.target();
        if (!result) {
            return null;
        }
        if (result instanceof Element) {
            return result;
        }
        // Vue component instance — try .$el
        if (result.$el instanceof Element) {
            return result.$el;
        }
        return null;
    }
    if (typeof props.target === "string") {
        return document.getElementById(props.target);
    }
    if (props.target instanceof Element) {
        return props.target;
    }
    return null;
}

// Map BPopover placement strings to floating-ui Placement
function mapPlacement(p: string): Placement {
    const map: Record<string, Placement> = {
        top: "top",
        bottom: "bottom",
        left: "left",
        right: "right",
        topleft: "top-start",
        topright: "top-end",
        bottomleft: "bottom-start",
        bottomright: "bottom-end",
        lefttop: "left-start",
        leftbottom: "left-end",
        righttop: "right-start",
        rightbottom: "right-end",
        auto: "bottom",
    };
    return map[p] || (p as Placement);
}

function getConfig(): Partial<ComputePositionConfig> {
    const useAltBoundary = props.boundary === "window";
    const middleware = [
        offset(10),
        flip({ altBoundary: useAltBoundary }),
        shift({ altBoundary: useAltBoundary, padding: 5 }),
    ];
    if (arrowEl.value) {
        middleware.push(arrow({ element: arrowEl.value }));
    }
    return {
        placement: mapPlacement(props.placement),
        middleware,
    };
}

const {
    x,
    y,
    placement: actualPlacement,
    middlewareData,
} = useFloatingPosition(resolveTarget, popoverEl, showState, getConfig);

// Bootstrap only defines .bs-popover-top/-right/-bottom/-left, and every arrow triangle rule
// hangs off those four, so an aligned floating-ui placement has to collapse to its base side --
// "bs-popover-bottom-start" matches no rule and leaves the arrow untriangled.
const basePlacement = computed(() => actualPlacement.value.split("-")[0]);

const arrowStyle = computed(() => {
    const arrowData = middlewareData.value.arrow;
    return {
        left: arrowData?.x != null ? `${arrowData.x}px` : "",
        top: arrowData?.y != null ? `${arrowData.y}px` : "",
    };
});

function showPopover() {
    showState.value = true;
}

function hidePopover() {
    showState.value = false;
}

function togglePopover() {
    showState.value = !showState.value;
}

watch(
    () => showState.value,
    async (visible) => {
        if (visible) {
            relocate();
            await nextTick();
            emit("shown");
        } else {
            emit("hidden");
        }
    },
);

// Watch for external show prop changes
watch(
    () => props.show,
    (val) => {
        if (val !== undefined) {
            isVisible.value = val;
        }
    },
);

// Parse triggers and set up event listeners
const parsedTriggers = computed(() => {
    const t = props.triggers;
    const result = new Set<string>();
    if (t.includes("hover")) {
        result.add("hover");
    }
    if (t.includes("click")) {
        result.add("click");
    }
    if (t.includes("focus")) {
        result.add("focus");
    }
    if (t.includes("blur")) {
        result.add("blur");
    }
    if (t.includes("manual")) {
        result.add("manual");
    }
    return result;
});

let activeListeners: Array<{ el: Element; event: string; handler: (e: Event) => void }> = [];
let hoverHideTimeout: ReturnType<typeof setTimeout> | null = null;

function cancelHoverHide() {
    if (hoverHideTimeout !== null) {
        clearTimeout(hoverHideTimeout);
        hoverHideTimeout = null;
    }
}

function deferredHide() {
    cancelHoverHide();
    hoverHideTimeout = setTimeout(() => {
        hidePopover();
        hoverHideTimeout = null;
    }, 100);
}

function setupListeners() {
    teardownListeners();

    if (parsedTriggers.value.has("manual")) {
        return;
    }

    const target = resolveTarget();
    if (!target) {
        return;
    }

    if (parsedTriggers.value.has("hover")) {
        const enterHandler = () => {
            cancelHoverHide();
            showPopover();
        };
        const leaveHandler = () => deferredHide();
        target.addEventListener("mouseenter", enterHandler);
        target.addEventListener("mouseleave", leaveHandler);
        activeListeners.push(
            { el: target, event: "mouseenter", handler: enterHandler },
            { el: target, event: "mouseleave", handler: leaveHandler },
        );
    }

    if (parsedTriggers.value.has("focus")) {
        const focusHandler = () => showPopover();
        const blurHandler = () => hidePopover();
        target.addEventListener("focus", focusHandler);
        target.addEventListener("blur", blurHandler);
        activeListeners.push(
            { el: target, event: "focus", handler: focusHandler },
            { el: target, event: "blur", handler: blurHandler },
        );
    }

    if (parsedTriggers.value.has("click")) {
        const clickHandler = () => togglePopover();
        target.addEventListener("click", clickHandler);
        activeListeners.push({ el: target, event: "click", handler: clickHandler });

        if (parsedTriggers.value.has("blur")) {
            // Close on click outside
            const outsideClickHandler = (e: Event) => {
                if (
                    showState.value &&
                    !target.contains(e.target as Node) &&
                    !popoverEl.value?.contains(e.target as Node)
                ) {
                    hidePopover();
                }
            };
            document.addEventListener("click", outsideClickHandler, true);
            activeListeners.push({ el: document as any, event: "click", handler: outsideClickHandler });
        }
    }

    // Keep popover open when hovering over it (bridges the offset gap)
    if (parsedTriggers.value.has("hover") && popoverEl.value) {
        const popoverEnter = () => {
            cancelHoverHide();
            showPopover();
        };
        const popoverLeave = () => deferredHide();
        popoverEl.value.addEventListener("mouseenter", popoverEnter);
        popoverEl.value.addEventListener("mouseleave", popoverLeave);
        activeListeners.push(
            { el: popoverEl.value, event: "mouseenter", handler: popoverEnter },
            { el: popoverEl.value, event: "mouseleave", handler: popoverLeave },
        );
    }
}

function teardownListeners() {
    cancelHoverHide();
    for (const { el, event, handler } of activeListeners) {
        el.removeEventListener(event, handler);
    }
    activeListeners = [];
}

// Move the popover out of its placeholder so ancestor overflow or transforms can't clip it. Done by
// hand rather than with vue2-teleport so the component has no Vue-2-only dependency. A trigger inside
// a modal <dialog> keeps its popover in that dialog: the rest of the page sits below the top layer
// and is inert while the dialog is open.
function relocate() {
    const el = popoverEl.value;
    const container = resolveTarget()?.closest("dialog") ?? document.body;
    if (el && el.parentElement !== container) {
        container.appendChild(el);
    }
}

onMounted(() => {
    // Delay setup slightly to ensure target elements are in DOM
    nextTick(() => {
        relocate();
        setupListeners();
        if (props.show) {
            isVisible.value = true;
        }
    });
});

// Re-setup listeners if target changes
watch(
    () => props.target,
    () => {
        nextTick(() => setupListeners());
    },
);

onBeforeUnmount(() => {
    teardownListeners();
    // Vue only removes the placeholder, which no longer holds the relocated popover.
    popoverEl.value?.remove();
});

defineExpose({
    show: showPopover,
    hide: hidePopover,
    toggle: togglePopover,
});
</script>

<template>
    <span class="g-popover-host" hidden>
        <div
            v-show="showState"
            ref="popoverEl"
            class="popover b-popover"
            :class="[customClass, `bs-popover-${basePlacement}`]"
            role="tooltip"
            :style="{ transform: `translate(${x}px, ${y}px)` }">
            <div ref="arrowEl" class="arrow" :style="arrowStyle" />
            <div v-if="title || $slots.title" class="popover-header">
                <slot name="title">{{ title }}</slot>
            </div>
            <div class="popover-body">
                <slot>{{ content }}</slot>
            </div>
        </div>
    </span>
</template>

<style scoped lang="scss">
.popover {
    position: absolute;
    top: 0;
    left: 0;
    z-index: 1060;
    max-width: 276px;

    .arrow {
        // The arrow middleware already centers this on the reference element, so Bootstrap's
        // horizontal margin would just shift it back off-center.
        margin: 0;
    }

    // GTable declares inline-size containment so it can drive its own container queries. That
    // makes its width independent of its contents, so it reports no intrinsic width at all --
    // and this box is shrink-to-fit, so it would collapse to the width of the title while the
    // table spilled out the side. Opt out of containment, and let long unbroken values like
    // email addresses wrap so the table still fits within max-width.
    :deep(.g-table-container) {
        container-type: normal;
    }

    :deep(.g-table) {
        th,
        td {
            overflow-wrap: anywhere;
        }
    }
}
</style>
