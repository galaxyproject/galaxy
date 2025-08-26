<script setup lang="ts">
/**
 * Tooltip component integrated into most interactive galaxy base components.
 * Can be used separately. Accepts rich content via slot.
 * Will set "aria-describedby" property on linked element.
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
import { watchImmediate } from "@vueuse/core";
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { useAccessibleHover } from "@/composables/accessibleHover";
import { useUid } from "@/composables/utils/uid";

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

const tooltipPositionStyle = ref<CSSTransform>();
const tooltipArrowPositionStyle = ref<CSSTransform>();

function getComputePositionConfig(arrowElement: HTMLDivElement): Partial<ComputePositionConfig> {
    return {
        placement: props.placement ?? "top",
        middleware: [
            offset(8),
            flip({
                altBoundary: true,
            }),
            shift({
                altBoundary: true,
            }),
            arrow({
                element: arrowElement,
            }),
        ],
    };
}

const finalPlacement = ref<Placement>("bottom");

async function updateTooltipPosition() {
    if (!props.reference || !tooltip.value || !tooltipArrow.value) {
        return;
    }

    const { x, y, middlewareData, placement } = await computePosition(
        props.reference,
        tooltip.value,
        getComputePositionConfig(tooltipArrow.value),
    );

    tooltipPositionStyle.value = `transform: translate(${x}px, ${y}px);`;

    if (middlewareData.arrow) {
        const { x, y } = middlewareData.arrow;
        tooltipArrowPositionStyle.value = `transform: translate(${x ?? 0}px, ${y ?? 0}px);`;
    }

    finalPlacement.value = placement;
}

let cleanupFunction: ReturnType<typeof autoUpdate> | null = null;

watch(
    () => isShowing.value,
    () => {
        cleanupFunction?.();

        if (isShowing.value && props.reference && tooltip.value) {
            cleanupFunction = autoUpdate(props.reference, tooltip.value, updateTooltipPosition);
        }
    },
);

useAccessibleHover(() => props.reference, show, hide);

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
