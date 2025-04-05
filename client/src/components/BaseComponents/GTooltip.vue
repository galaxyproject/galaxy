<script setup lang="ts">
import type { Instance as PopperInstance, Placement } from "@popperjs/core";
import { createPopper } from "@popperjs/core";
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
