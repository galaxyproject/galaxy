<script setup lang="ts">
import type { Placement } from "@popperjs/core";
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

import { useAccessibleHover } from "@/composables/accessibleHover";
import { useResolveElement } from "@/composables/resolveElement";
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
    transparent?: boolean;
    pill?: boolean;
    pressed?: boolean;
}>();

const emit = defineEmits<{
    (e: "click", event: PointerEvent): void;
    (e: "update:pressed", pressed: boolean): void;
}>();

function onClick(event: PointerEvent) {
    if (!props.disabled) {
        emit("click", event);
        emit("update:pressed", !props.pressed);
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
        "g-transparent": props.transparent,
        "g-pressed": props.pressed,
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

const buttonRef = ref<HTMLElement | InstanceType<typeof RouterLink> | null>(null);
const tooltipRef = ref<InstanceType<typeof GTooltip>>();

const buttonElementRef = useResolveElement(buttonRef);

useAccessibleHover(
    buttonElementRef,
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
        :data-title="currentTooltip"
        :data-disabled="props.disabled"
        :class="{ ...variantClasses, ...styleClasses }"
        :to="props.to"
        :href="props.to ?? props.href"
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
            :reference="buttonElementRef"
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

    &:focus {
        outline: none;
        box-shadow: 0 0 0 0.2rem rgb(from var(--color-blue-400) r g b / 0.33);
        z-index: 999;
    }

    &:focus-visible {
        outline: none;
        box-shadow: 0 0 0 0.2rem var(--color-blue-400);
        z-index: 999;
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
        &:focus-visible {
            background-color: var(--color-grey-300);
            border-color: var(--color-grey-400);

            &:active {
                background-color: var(--color-grey-400);
                border-color: var(--color-grey-600);
            }
        }

        &:focus-visible {
            border-color: var(--color-grey-600);
        }

        &.g-outline.g-pressed {
            background-color: var(--color-grey-600);
            color: var(--color-grey-100);
            border-color: var(--color-grey-800);
        }
    }

    @each $color in "blue", "green", "red", "yellow", "orange" {
        &.g-#{$color} {
            background-color: var(--color-#{$color}-600);
            border-color: var(--color-#{$color}-600);
            color: var(--color-#{$color}-100);

            &:hover,
            &:focus-visible {
                background-color: var(--color-#{$color}-700);
                border-color: var(--color-#{$color}-700);

                &:active {
                    background-color: var(--color-#{$color}-600);
                    color: var(--color-#{$color}-100);
                }
            }

            &:focus-visible {
                border-color: var(--color-#{$color}-900);
            }
        }

        &.g-outline:not(.g-pressed).g-#{$color} {
            border-color: var(--color-#{$color}-600);
            color: var(--color-#{$color}-600);

            &:hover {
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

    &.g-outline:not(.g-pressed) {
        background-color: var(--background-color);
    }

    &.g-disabled {
        background-color: var(--color-grey-100);
        border-color: var(--color-grey-200);
        color: var(--color-grey-500);

        &:hover,
        &:focus-visible {
            background-color: var(--color-grey-100);
            border-color: var(--color-grey-200);

            &:active {
                background-color: var(--color-grey-100);
                border-color: var(--color-grey-200);
                color: var(--color-grey-500);
            }
        }

        &:focus-visible {
            border-color: var(--color-grey-500);
        }

        &.g-outline {
            background-color: var(--background-color);
            border-color: var(--color-grey-400);
            color: var(--color-grey-400);

            &:hover,
            &:focus,
            &:focus-visible {
                background-color: var(--background-color);
                border-color: var(--color-grey-400);
                color: var(--color-grey-400);
            }

            &:focus-visible {
                border-color: var(--color-grey-800);
                background-color: var(--background-color);
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
        aspect-ratio: 1;
        display: inline-flex;
        justify-content: center;

        &.g-small,
        &.g-medium {
            padding: var(--spacing-1);
        }

        &.g-large {
            padding: var(--spacing-2);
        }

        &.g-inline {
            padding: 2px;
        }
    }

    &.g-transparent {
        border: none;
        background-color: rgb(100% 100% 100% / 0);

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
