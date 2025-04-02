<script setup lang="ts">
import type { Placement } from "@popperjs/core";
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

import { useAccessibleHover } from "@/composables/accessibleHover";
import { useUid } from "@/composables/utils/uid";

import { type ComponentColor, type ComponentSize, type ComponentVariantClassList, prefix } from "./componentVariants";

import GTooltip from "./GTooltip.vue";

const props = defineProps<{
    href?: string;
    to?: string;
    color?: ComponentColor;
    outline?: boolean;
    disabled?: boolean;
    title?: string;
    disabledTitle?: string;
    size?: ComponentSize;
    tooltip?: boolean;
    tooltipPlacement?: Placement;
    inline?: boolean;
    iconOnly?: boolean;
    pill?: boolean;
}>();

const emit = defineEmits<{
    (e: "click", event: PointerEvent): void;
}>();

function onClick(event: PointerEvent) {
    if (!props.disabled) {
        emit("click", event);
    }
}

const variantClasses = computed(() => {
    const classObject = {} as ComponentVariantClassList;
    classObject[prefix(props.color ?? "grey")] = true;
    classObject[prefix(props.size ?? "medium")] = true;
    return classObject;
});

const styleClasses = computed(() => {
    return {
        "g-outline": props.outline,
        "g-disabled": props.disabled,
        "g-icon-only": props.iconOnly,
        "g-inline": props.inline,
        "g-pill": props.pill,
    };
});

const baseComponent = computed(() => {
    if (props.to) {
        return RouterLink;
    } else if (props.href) {
        return "a" as const;
    } else {
        return "button" as const;
    }
});

const currentTooltip = computed(() => {
    if (props.disabled) {
        return props.disabledTitle ?? props.title;
    } else {
        return props.title;
    }
});

const currentTitle = computed(() => {
    if (props.tooltip) {
        return false;
    } else {
        return currentTooltip.value;
    }
});

const tooltipId = useUid("g-tooltip");
const describedBy = computed(() => {
    if (props.tooltip) {
        return tooltipId.value;
    } else {
        return false;
    }
});

const buttonRef = ref<HTMLElement | null>(null);
const tooltipRef = ref<InstanceType<typeof GTooltip>>();

useAccessibleHover(
    buttonRef,
    () => {
        tooltipRef.value?.show();
    },
    () => {
        tooltipRef.value?.hide();
    }
);
</script>

<template>
    <component
        :is="baseComponent"
        ref="buttonRef"
        class="g-button"
        :class="{ ...variantClasses, ...styleClasses }"
        :to="props.to"
        :href="props.href"
        :title="currentTitle"
        :aria-describedby="describedBy"
        v-bind="$attrs"
        @click="onClick">
        <slot></slot>

        <!-- TODO: make tooltip a sibling in Vue 3 -->
        <GTooltip
            v-if="props.tooltip"
            :id="tooltipId"
            ref="tooltipRef"
            :reference="buttonRef"
            :text="currentTooltip"
            :placement="props.tooltipPlacement" />
    </component>
</template>

<style scoped lang="scss">
.g-button {
    display: inline-block;
    margin: 0;
    border: 1px solid;
    border-radius: var(--spacing-1);
    text-decoration: none;
    vertical-align: middle;
    cursor: pointer;

    transition: color 0.15s ease-in-out, background-color 0.15s ease-in-out, border-color 0.15s ease-in-out,
        box-shadow 0.15s ease-in-out;

    @media (prefers-reduced-motion) {
        transition: none;
    }

    &:focus-visible {
        box-shadow: 0 0 0 0.2rem var(--color-blue-400);
    }

    // sizes
    &.g-small {
        font-size: var(--font-size-small);
        padding: var(--spacing-1) var(--spacing-2);
    }

    &.g-medium {
        font-size: var(--font-size-medium);
        padding: var(--spacing-1) var(--spacing-2);
    }

    &.g-large {
        font-size: var(--font-size-large);
        padding: var(--spacing-2) var(--spacing-3);
    }

    // colors
    &.g-grey {
        background-color: var(--color-grey-200);
        border-color: var(--color-grey-300);
        color: var(--color-grey-800);

        &:hover,
        &:focus,
        &:focus-visible {
            background-color: var(--color-grey-300);
            border-color: var(--color-grey-400);
        }

        &:active {
            background-color: var(--color-grey-400);
            border-color: var(--color-grey-600);
        }

        &:focus-visible {
            border-color: var(--color-grey-600);
        }
    }

    @each $color in "blue", "green", "red", "yellow", "orange" {
        &.g-#{$color} {
            background-color: var(--color-#{$color}-600);
            border-color: var(--color-#{$color}-600);
            color: var(--color-#{$color}-100);

            &:hover,
            &:focus,
            &:focus-visible {
                background-color: var(--color-#{$color}-700);
                border-color: var(--color-#{$color}-700);
            }

            &:active {
                background-color: var(--color-#{$color}-600);
                color: var(--color-#{$color}-100);
            }

            &:focus-visible {
                border-color: var(--color-#{$color}-900);
            }
        }

        &.g-outline.g-#{$color} {
            background-color: rgb(100% 100% 100% / 0);
            border-color: var(--color-#{$color}-600);
            color: var(--color-#{$color}-600);

            &:hover,
            &:focus,
            &:focus-visible {
                background-color: var(--color-#{$color}-600);
                border-color: var(--color-#{$color}-600);
                color: var(--color-#{$color}-100);
            }

            &:focus-visible {
                border-color: var(--color-#{$color}-900);
                background-color: var(--color-#{$color}-200);
                color: var(--color-#{$color}-600);
            }
        }
    }

    &.g-disabled {
        background-color: var(--color-grey-100);
        border-color: var(--color-grey-200);
        color: var(--color-grey-500);

        &:hover,
        &:focus,
        &:focus-visible {
            background-color: var(--color-grey-100);
            border-color: var(--color-grey-200);
        }

        &:active {
            background-color: var(--color-grey-100);
            border-color: var(--color-grey-200);
            color: var(--color-grey-500);
        }

        &:focus-visible {
            border-color: var(--color-grey-500);
        }

        &.g-outline {
            background-color: rgb(100% 100% 100% / 0);
            border-color: var(--color-grey-400);
            color: var(--color-grey-400);

            &:hover,
            &:focus,
            &:focus-visible {
                background-color: rgb(100% 100% 100% / 0);
                border-color: var(--color-grey-400);
                color: var(--color-grey-400);
            }

            &:focus-visible {
                border-color: var(--color-grey-800);
                background-color: rgb(100% 100% 100% / 0);
                color: var(--color-grey-500);
            }
        }
    }

    // variants
    &.g-inline {
        display: inline;
        padding-top: 0;
        padding-bottom: 0;
    }

    &.g-pill {
        border-radius: 100rem;
    }

    &.g-icon-only {
        border: none;
        background-color: rgb(100% 100% 100% / 0);
        padding: var(--spacing-1);
        aspect-ratio: 1;
        display: inline-flex;
        justify-content: center;

        &.g-inline {
            padding: 2px;
        }

        @each $color in "blue", "green", "red", "yellow", "orange" {
            &.g-#{$color} {
                color: var(--color-#{$color}-600);

                &:hover,
                &:focus,
                &:focus-visible {
                    background-color: var(--color-#{$color}-600);
                    color: var(--color-#{$color}-100);
                }
            }
        }
    }
}
</style>
