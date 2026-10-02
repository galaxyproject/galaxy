<script setup lang="ts">
/**
 * Tooltip component integrated into most interactive galaxy base components.
 * Can be used separately. Accepts rich content via slot.
 * Will set "aria-describedby" property on linked element.
 */

import { arrow, type ComputePositionConfig, flip, offset, type Placement, shift } from "@floating-ui/dom";
import { watchImmediate } from "@vueuse/core";
import { computed, onBeforeUnmount, ref } from "vue";

import { useAccessibleHover } from "../composables/accessibleHover";
import { useFloatingPosition } from "../composables/floatingPosition";
import { useUid } from "../composables/uid";
import { DEFAULT_TOOLTIP_HOVER_DELAY_MS } from "../utils/tooltipTiming";

const props = defineProps<{
    /** Optional id override. Will auto generate an id if none is provided */
    id?: string;
    /** Element to listen to on hover state. Will also set "aria-describedby" attribute of linked element to this tooltip */
    reference: HTMLElement | null;
    /** Optional text. Alternative to using the elements slot */
    text?: string;
    /** Position of the tooltip relative to reference element */
    placement?: Placement;
}>();

const tooltip = ref<HTMLDivElement>();
const tooltipArrow = ref<HTMLDivElement>();
const isShowing = ref(false);
const uid = useUid("g-tooltip");
const elementId = computed(() => props.id ?? uid.value);

let previousReference: HTMLElement | null = null;

watchImmediate(
    () => [props.reference, elementId.value],
    () => {
        if (previousReference !== null) {
            previousReference.removeAttribute("aria-describedby");
        }

        if (props.reference !== null) {
            props.reference.setAttribute("aria-describedby", elementId.value);
        }

        previousReference = props.reference;
    },
);

onBeforeUnmount(() => {
    props.reference?.removeAttribute("aria-describedby");
});

function show() {
    isShowing.value = true;
}

function hide() {
    isShowing.value = false;
}

type CSSTransform = `transform: translate(${number}px, ${number}px);`;

function getComputePositionConfig(): Partial<ComputePositionConfig> {
    const middleware = [
        offset(8),
        flip({
            altBoundary: true,
        }),
        shift({
            altBoundary: true,
        }),
    ];
    if (tooltipArrow.value) {
        middleware.push(
            arrow({
                element: tooltipArrow.value,
            }),
        );
    }
    return {
        placement: props.placement ?? "top",
        middleware,
    };
}

const {
    x,
    y,
    placement: finalPlacement,
    middlewareData,
} = useFloatingPosition(() => props.reference, tooltip, isShowing, getComputePositionConfig);

const tooltipPositionStyle = computed<CSSTransform>(() => `transform: translate(${x.value}px, ${y.value}px);`);

const tooltipArrowPositionStyle = computed<CSSTransform | undefined>(() => {
    const arrowData = middlewareData.value.arrow;
    return arrowData ? `transform: translate(${arrowData.x ?? 0}px, ${arrowData.y ?? 0}px);` : undefined;
});

useAccessibleHover(() => props.reference, show, hide, {
    showDelayMs: DEFAULT_TOOLTIP_HOVER_DELAY_MS,
    delayFocusEnter: false,
});

defineExpose({
    show,
    hide,
});
</script>

<template>
    <div
        :id="elementId"
        ref="tooltip"
        role="tooltip"
        class="g-tooltip"
        :class="{ 'sr-only': !isShowing }"
        :style="tooltipPositionStyle"
        :data-show="isShowing">
        <slot></slot>
        {{ props.text ?? "" }}
        <div
            ref="tooltipArrow"
            class="g-tooltip-arrow"
            :style="tooltipArrowPositionStyle"
            :data-placement="finalPlacement"></div>
    </div>
</template>

<style lang="scss" scoped>
.g-tooltip {
    background-color: var(--color-blue-800);
    color: var(--color-grey-100);
    padding: var(--spacing-1) var(--spacing-2);
    font-size: var(--font-size-small);
    border-radius: var(--spacing-1);
    pointer-events: none;
    font-weight: 400;
    z-index: 9999;

    width: max-content;
    position: absolute;
    top: 0;
    left: 0;

    &:not(.sr-only) {
        display: block;
    }

    .g-tooltip-arrow {
        visibility: hidden;

        &,
        &::before {
            position: absolute;
            width: 8px;
            height: 8px;
            background: inherit;
            z-index: -1;

            top: 0;
            left: 0;
        }

        &::before {
            visibility: visible;
            content: "";
            transform: rotate(45deg);
        }

        &[data-placement^="top"] {
            top: unset;
            bottom: -4px;
        }

        &[data-placement^="bottom"] {
            top: -4px;
            bottom: unset;
        }

        &[data-placement^="left"] {
            left: unset;
            right: -4px;
        }

        &[data-placement^="right"] {
            left: -4px;
            right: unset;
        }
    }
}
</style>
