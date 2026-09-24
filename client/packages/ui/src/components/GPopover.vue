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
import { useUid } from "../composables/uid";
import { computeHoverBridge, computeHoverGap, isPointInPolygon, type Point } from "../utils/hoverBridge";
import {
    DEFAULT_TOOLTIP_HOVER_DELAY_MS,
    INTERACTIVE_POPOVER_CLOSE_DELAY_MS,
    useDelayedAction,
} from "../utils/tooltipTiming";

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

const popoverId = useUid("g-popover-");
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

// Same timing as GTooltip and Popper: hovering opens after the shared delay, and leaving closes after
// a short grace period that reaching the popover (or returning to the trigger) cancels.
const openDelay = useDelayedAction(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
const closeDelay = useDelayedAction(INTERACTIVE_POPOVER_CLOSE_DELAY_MS);

function cancelScheduled() {
    openDelay.clear();
    closeDelay.clear();
    endHoverBridge();
}

// The pointer reached the trigger or the popover, so a pending close or crossing is over.
function holdOpen() {
    closeDelay.clear();
    endHoverBridge();
}

function scheduleOpen() {
    holdOpen();
    if (!showState.value && !openDelay.isScheduled()) {
        openDelay.schedule(showPopover);
    }
}

function scheduleClose() {
    openDelay.clear();
    closeDelay.schedule(hidePopover);
}

// Where the pointer may go after leaving the trigger or popover without closing it (safe triangle).
let hoverBridge: Point[] | null = null;

// floating-ui's safePolygon ends a crossing 40 ms after the pointer stops; slower hands get longer here.
const HOVER_BRIDGE_REST_MS = 300;
const bridgeRest = useDelayedAction(HOVER_BRIDGE_REST_MS);

function leaveHoverBridge() {
    endHoverBridge();
    scheduleClose();
}

function onBridgeMove(event: Event) {
    const { clientX, clientY } = event as PointerEvent;
    if (hoverBridge && isPointInPolygon([clientX, clientY], hoverBridge)) {
        bridgeRest.schedule(onBridgeRest);
    } else {
        leaveHoverBridge();
    }
}

// A pointer that stopped short of both elements is no longer crossing.
function onBridgeRest() {
    if ([resolveTarget(), popoverEl.value].some((el) => el?.matches(":hover"))) {
        holdOpen();
    } else {
        leaveHoverBridge();
    }
}

// No more pointer events arrive here once the pointer leaves the window or enters an iframe, or a pen leaves range.
function onBridgeOut(event: Event) {
    const next = (event as PointerEvent).relatedTarget;
    if (!next || next instanceof HTMLIFrameElement) {
        leaveHoverBridge();
    }
}

// Captured to see any element's scroll; a scroll or wheel leaves the stored area stale.
const bridgeListeners: Array<[string, (event: Event) => void]> = [
    ["pointermove", onBridgeMove],
    ["pointerdown", leaveHoverBridge],
    ["pointercancel", leaveHoverBridge],
    ["pointerout", onBridgeOut],
    ["pointerleave", onBridgeOut],
    ["scroll", leaveHoverBridge],
    ["wheel", leaveHoverBridge],
];

// A mouse or pen heading from one element to the other keeps the popover open (WCAG 2.1 SC 1.4.13, hoverable).
function startHoverBridge(event: Event, leavingTrigger: boolean) {
    const { pointerType, clientX, clientY } = event as PointerEvent;
    const target = resolveTarget();
    if (pointerType === "touch" || !showState.value || !target || !popoverEl.value) {
        return;
    }
    const triggerRect = target.getBoundingClientRect();
    const popoverRect = popoverEl.value.getBoundingClientRect();
    // Heading back, only the gap straight between the two counts, so the trigger's row stays out.
    const bridge = leavingTrigger
        ? computeHoverBridge([clientX, clientY], triggerRect, popoverRect)
        : computeHoverGap(triggerRect, popoverRect);
    // Nothing to cross when leaving away from the other element or when the two touch; mouseleave closes as usual.
    if (!bridge.length) {
        return;
    }
    hoverBridge = bridge;
    for (const [type, handler] of bridgeListeners) {
        document.addEventListener(type, handler, { capture: true, passive: true });
    }
    bridgeRest.schedule(onBridgeRest);
}

function endHoverBridge() {
    hoverBridge = null;
    bridgeRest.clear();
    for (const [type, handler] of bridgeListeners) {
        document.removeEventListener(type, handler, true);
    }
}

// pointerleave, which runs first, may have started a crossing; otherwise close after the usual delay.
function onHoverLeave() {
    if (!hoverBridge) {
        scheduleClose();
    }
}

function showPopover() {
    cancelScheduled();
    showState.value = true;
}

function hidePopover() {
    cancelScheduled();
    showState.value = false;
}

function togglePopover() {
    cancelScheduled();
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
        // The parent decided, so a pending hover open or close must not undo it.
        cancelScheduled();
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

let linkedAttributes: Array<{ el: Element; attribute: string }> = [];

// Adds the popover id to an id-list attribute such as aria-describedby, keeping ids other components
// (a v-g-tooltip on the same trigger, say) have put there.
function linkIdReference(el: Element, attribute: string) {
    const ids = (el.getAttribute(attribute) ?? "").split(/\s+/).filter(Boolean);
    if (!ids.includes(popoverId.value)) {
        el.setAttribute(attribute, [...ids, popoverId.value].join(" "));
    }
    linkedAttributes.push({ el, attribute });
}

function removeIdReference(el: Element, attribute: string, id: string) {
    const ids = (el.getAttribute(attribute) ?? "").split(/\s+/).filter((existing) => existing && existing !== id);
    if (ids.length) {
        el.setAttribute(attribute, ids.join(" "));
    } else {
        el.removeAttribute(attribute);
    }
}

let activeListeners: Array<{ el: EventTarget; event: string; handler: (e: Event) => void; capture: boolean }> = [];

function listen(el: EventTarget, event: string, handler: (e: Event) => void, capture = false) {
    el.addEventListener(event, handler, capture);
    activeListeners.push({ el, event, handler, capture });
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
        listen(target, "mouseenter", scheduleOpen);
        listen(target, "pointerleave", (event) => startHoverBridge(event, true));
        listen(target, "mouseleave", onHoverLeave);
    }

    if (parsedTriggers.value.has("hover") || parsedTriggers.value.has("focus")) {
        // Screen readers announce the popover content as the trigger's description, as for GTooltip.
        linkIdReference(target, "aria-describedby");
    }

    if (parsedTriggers.value.has("focus")) {
        listen(target, "focus", showPopover);
        listen(target, "blur", hidePopover);
    }

    if (parsedTriggers.value.has("click")) {
        listen(target, "click", togglePopover);

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
            listen(document, "click", outsideClickHandler, true);
        }
    }

    // Keep popover open when hovering over it
    if (parsedTriggers.value.has("hover") && popoverEl.value) {
        listen(popoverEl.value, "mouseenter", holdOpen);
        listen(popoverEl.value, "pointerleave", (event) => startHoverBridge(event, false));
        listen(popoverEl.value, "mouseleave", onHoverLeave);
    }
}

function teardownListeners() {
    cancelScheduled();
    for (const { el, event, handler, capture } of activeListeners) {
        el.removeEventListener(event, handler, capture);
    }
    activeListeners = [];
    for (const { el, attribute } of linkedAttributes) {
        removeIdReference(el, attribute, popoverId.value);
    }
    linkedAttributes = [];
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
            :id="popoverId"
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
    // Bootstrap spaces .bs-popover-* from the trigger with a margin, but floating-ui ignores margins,
    // so bottom/right placements ended up further away than top/left. offset() alone sets the gap.
    margin: 0;

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
