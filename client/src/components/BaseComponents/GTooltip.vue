<script setup lang="ts">
import type { Instance as PopperInstance, Placement } from "@popperjs/core";
import { createPopper } from "@popperjs/core";
import flip from "@popperjs/core/lib/modifiers/flip";
import { watchImmediate } from "@vueuse/core";
import { ref } from "vue";

import { assertDefined } from "@/utils/assertions";

const props = defineProps<{
    id: string;
    reference: HTMLElement | null;
    text?: string;
    placement?: Placement;
}>();

const tooltip = ref<HTMLDivElement>();
const popperInstance = ref<PopperInstance | null>(null);
const isShowing = ref(false);

watchImmediate(
    () => [props.id, props.reference],
    () => {
        popperInstance.value?.destroy();

        if (!props.reference) {
            console.warn(`no reference defined for tooltip with id ${props.id}`);
            return;
        }

        assertDefined(tooltip.value);

        popperInstance.value = createPopper(props.reference, tooltip.value, {
            placement: props.placement ?? "auto",
            modifiers: [
                flip,
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
            ],
        });
    }
);

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

defineExpose({
    show,
    hide,
});
</script>

<template>
    <div
        :id="props.id"
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

    &:not(.sr-only) {
        display: block;
    }

    .g-tooltip-arrow {
        visibility: hidden;

        &,
        &::before {
            position: absolute;
            width: 9px;
            height: 9px;
            background: inherit;
        }

        &::before {
            visibility: visible;
            content: "";
            transform: rotate(45deg);
        }
    }

    &[data-popper-placement^="top"] > .g-tooltip-arrow {
        bottom: -4.5px;
    }

    &[data-popper-placement^="bottom"] > .g-tooltip-arrow {
        top: -4.5px;
    }

    &[data-popper-placement^="left"] > .g-tooltip-arrow {
        right: -4.5px;
    }

    &[data-popper-placement^="right"] > .g-tooltip-arrow {
        left: -4.5px;
    }
}
</style>
