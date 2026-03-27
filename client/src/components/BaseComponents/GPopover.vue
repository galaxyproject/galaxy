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

import {
    arrow,
    autoUpdate,
    computePosition,
    type ComputePositionConfig,
    flip,
    offset,
    type Placement,
    shift,
} from "@floating-ui/dom";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

type TriggerType = "hover" | "click" | "click blur" | "hover focus" | "manual" | "focus";

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
const actualPlacement = ref<Placement>("bottom");

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

const popoverPosition = ref({ x: 0, y: 0 });
const arrowPosition = ref<{ x?: number; y?: number }>({});
let cleanupAutoUpdate: ReturnType<typeof autoUpdate> | null = null;

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

async function updatePosition() {
    const target = resolveTarget();
    if (!target || !popoverEl.value) {
        return;
    }
    const result = await computePosition(target, popoverEl.value, getConfig());
    popoverPosition.value = { x: result.x, y: result.y };
    actualPlacement.value = result.placement;
    if (result.middlewareData.arrow) {
        arrowPosition.value = { x: result.middlewareData.arrow.x, y: result.middlewareData.arrow.y };
    }
}

function showPopover() {
    showState.value = true;
}

function hidePopover() {
    showState.value = false;
}

function togglePopover() {
    showState.value = !showState.value;
}

// Setup auto-update when visible
watch(
    () => showState.value,
    async (visible) => {
        cleanupAutoUpdate?.();
        cleanupAutoUpdate = null;

        if (visible) {
            await nextTick();
            const target = resolveTarget();
            if (target && popoverEl.value) {
                cleanupAutoUpdate = autoUpdate(target, popoverEl.value, updatePosition);
            }
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
    if (t === "manual") {
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

onMounted(() => {
    // Delay setup slightly to ensure target elements are in DOM
    nextTick(() => {
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
    cleanupAutoUpdate?.();
});

defineExpose({
    show: showPopover,
    hide: hidePopover,
    toggle: togglePopover,
});
</script>

<template>
    <div
        v-show="showState"
        ref="popoverEl"
        class="popover b-popover"
        :class="[customClass, `bs-popover-${actualPlacement}`]"
        role="tooltip"
        :style="{ transform: `translate(${popoverPosition.x}px, ${popoverPosition.y}px)` }">
        <div
            ref="arrowEl"
            class="arrow"
            :style="{
                left: arrowPosition.x != null ? `${arrowPosition.x}px` : '',
                top: arrowPosition.y != null ? `${arrowPosition.y}px` : '',
            }" />
        <div v-if="title || $slots.title" class="popover-header">
            <slot name="title">{{ title }}</slot>
        </div>
        <div class="popover-body">
            <slot>{{ content }}</slot>
        </div>
    </div>
</template>

<style scoped lang="scss">
.popover {
    position: absolute;
    top: 0;
    left: 0;
    z-index: 1060;
    max-width: 276px;
}
</style>
