<script setup lang="ts">
/**
 * Tooltip component integrated into most interactive galaxy base components.
 * Can be used separately. Accepts rich content via slot.
 * Will set "aria-describedby" property on linked element.
 */

import type { Instance as PopperInstance, Placement } from "@popperjs/core";
import { createPopper } from "@popperjs/core";
import { watchImmediate } from "@vueuse/core";
import { computed, onUnmounted, ref } from "vue";

import { useAccessibleHover } from "@/composables/accessibleHover";
import { useUid } from "@/composables/utils/uid";
import { assertDefined } from "@/utils/assertions";

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
const popperInstance = ref<PopperInstance | null>(null);
const isShowing = ref(false);
const uid = useUid("g-tooltip");
const elementId = computed(() => props.id ?? uid.value);

let previousReference: HTMLElement | null = null;

watchImmediate(
    () => [props.reference, elementId.value],
    () => {
        popperInstance.value?.destroy();

        if (previousReference !== null) {
            previousReference.removeAttribute("aria-describedby");
        }

        if (props.reference !== null) {
            props.reference.setAttribute("aria-describedby", elementId.value);
        }

        previousReference = props.reference;

        if (!props.reference) {
            return;
        }

        assertDefined(tooltip.value);

        popperInstance.value = createPopper(props.reference, tooltip.value, {
            placement: props.placement ?? "top",
            modifiers: [
                {
                    name: "flip",
                },
                {
                    name: "offset",
                    options: {
                        offset: [0, 8],
                    },
                },
                {
                    name: "preventOverflow",
                    options: {
                        altBoundary: true,
                    },
                },
                {
                    name: "arrow",
                    options: {
                        padding: 8,
                    },
                },
            ],
        });
    }
);

onUnmounted(() => {
    props.reference?.removeAttribute("aria-describedby");
});

function show() {
    isShowing.value = true;

    popperInstance.value?.setOptions((options) => ({
        ...options,
        modifiers: [...(options.modifiers ?? []), { name: "eventListeners", enabled: true }],
    }));

    popperInstance.value?.update();
}

function hide() {
    isShowing.value = false;

    popperInstance.value?.setOptions((options) => ({
        ...options,
        modifiers: [...(options.modifiers ?? []), { name: "eventListeners", enabled: false }],
    }));
}

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
        :data-show="isShowing">
        <slot></slot>
        {{ props.text ?? "" }}
        <div class="g-tooltip-arrow" data-popper-arrow></div>
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
        }

        &::before {
            visibility: visible;
            content: "";
            transform: translateX(-4px) rotate(45deg);
        }
    }

    &[data-popper-placement^="top"] > .g-tooltip-arrow {
        bottom: -4px;
    }

    &[data-popper-placement^="bottom"] > .g-tooltip-arrow {
        top: -4px;
    }

    &[data-popper-placement^="left"] > .g-tooltip-arrow {
        right: -4px;
    }

    &[data-popper-placement^="right"] > .g-tooltip-arrow {
        left: -4px;
    }
}
</style>
