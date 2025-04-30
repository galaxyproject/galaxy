<script setup lang="ts">
/**
 * Button-like element that can be used for buttons, anchors, or router-links.
 * Defaults to button behavior.
 */

import type { Placement } from "@popperjs/core";
import { computed, ref } from "vue";
import { type RouterLink } from "vue-router";

import { useClickableElement } from "@/components/BaseComponents/composables/clickableElement";
import { useCurrentTitle } from "@/components/BaseComponents/composables/currentTitle";
import { useResolveElement } from "@/composables/resolveElement";

import { type ComponentColor, type ComponentSize, type ComponentVariantClassList, prefix } from "./componentVariants";

import GTooltip from "./GTooltip.vue";

const props = defineProps<{
    /** Href to set on the underlying 'a' element. Using this will turn the element into an anchor, not affecting the styling */
    href?: string;
    /** Router link "to" prop. Using this will turn the element into a router-link, not affecting the styling  */
    to?: string;
    /** Which color scheme to use for the component. Not setting this will make the button appear grey */
    color?: ComponentColor;
    /** Outline variant of the button. Can be used together with the `pressed` state */
    outline?: boolean;
    /** Disabled state. Changes appearance, and will no longer accept or forward clicks */
    disabled?: boolean;
    /** Title attribute, or tooltip text */
    title?: string;
    /** Alternative title to be displayed in a disabled state */
    disabledTitle?: string;
    /** Displayed size of the component */
    size?: ComponentSize;
    /** When set, uses a tooltip for the "title" prop, instead of the native title attribute */
    tooltip?: boolean;
    /** Controls the positioning of the tooltip, if a tooltip is active */
    tooltipPlacement?: Placement;
    /** Inline variant of the button. Affects buttons size, and positioning */
    inline?: boolean;
    /** Small, icon-only variant of the button */
    iconOnly?: boolean;
    /** Variant of the button without background or outline. Can be used together with the `pressed` state */
    transparent?: boolean;
    /** Variant of the button with more rounded corners */
    pill?: boolean;
    /** Pressed state allows for a toggle-like behavior of the button. For use with the outline and transparent variants */
    pressed?: boolean;
}>();

const emit = defineEmits<{
    (e: "click", event: PointerEvent): void;
    (e: "update:pressed", pressed: boolean): void;
}>();

function onClick(event: PointerEvent) {
    if (props.disabled) {
        event.preventDefault();
    } else {
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

const baseComponent = useClickableElement(props);
const currentTitle = useCurrentTitle(props);

const showTooltip = computed(() => props.tooltip && currentTitle.value);

const buttonRef = ref<HTMLElement | InstanceType<typeof RouterLink> | null>(null);
const buttonElementRef = useResolveElement(buttonRef);
</script>

<template>
    <component
        :is="baseComponent"
        ref="buttonRef"
        class="g-button"
        :data-title="currentTitle"
        :class="{ ...variantClasses, ...styleClasses }"
        :to="!props.disabled ? props.to : ''"
        :href="!props.disabled ? props.to ?? props.href : ''"
        :title="props.tooltip ? false : currentTitle"
        :aria-disabled="props.disabled"
        v-bind="$attrs"
        @click="onClick">
        <slot></slot>

        <!-- TODO: make tooltip a sibling in Vue 3 -->
        <GTooltip
            v-if="showTooltip"
            :reference="buttonElementRef"
            :text="currentTitle"
            :placement="props.tooltipPlacement" />
    </component>
</template>

<style scoped lang="scss">
.g-button {
    display: inline-flex;
    gap: var(--spacing-1);
    align-items: center;
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
        background-color: var(--color-grey-100) !important;
        border-color: var(--color-grey-200) !important;
        color: var(--color-grey-500) !important;

        &:focus-visible {
            border-color: var(--color-grey-500) !important;
        }

        &.g-outline {
            background-color: var(--background-color) !important;
            border-color: var(--color-grey-400) !important;
            color: var(--color-grey-400) !important;

            &:focus-visible {
                border-color: var(--color-grey-800) !important;
                background-color: var(--background-color) !important;
                color: var(--color-grey-500) !important;
            }
        }

        &.g-transparent {
            background-color: rgb(100% 100% 100% / 0) !important;
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

    &.g-transparent:not(.g-pressed) {
        border: 1px solid rgb(100% 100% 100% / 0);
        background-color: rgb(100% 100% 100% / 0);

        @each $color in "blue", "green", "red", "yellow", "orange" {
            &.g-#{$color} {
                color: var(--color-#{$color}-600);

                &:hover,
                &:focus-visible {
                    background-color: var(--color-#{$color}-600);
                    color: var(--color-#{$color}-100);
                }
            }
        }
    }
}
</style>
