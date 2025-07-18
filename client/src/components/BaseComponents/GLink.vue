<script setup lang="ts">
/**
 * Clickable inline text element that can be used for router links, anchors, or inline text buttons.
 * Defaults to button behavior.
 */

import type { Placement } from "@floating-ui/dom";
import { computed, ref } from "vue";
import type { RouterLink } from "vue-router";

import { useClickableElement } from "@/components/BaseComponents/composables/clickableElement";
import { useCurrentTitle } from "@/components/BaseComponents/composables/currentTitle";
import { useResolveElement } from "@/composables/resolveElement";

import GTooltip from "@/components/BaseComponents/GTooltip.vue";

const props = defineProps<{
    /** Href to set on the underlying 'a' element. Using this will turn the element into an anchor, not affecting the styling */
    href?: string;
    /** Router link "to" prop. Using this will turn the element into a router-link, not affecting the styling  */
    to?: string;
    /** Disabled state. Changes appearance, and will no longer accept or forward clicks */
    disabled?: boolean;
    /** Title attribute, or tooltip text */
    title?: string;
    /** Alternative title to be displayed in a disabled state */
    disabledTitle?: string;
    /** When set, uses a tooltip for the "title" prop, instead of the native title attribute */
    tooltip?: boolean;
    /** Controls the positioning of the tooltip, if a tooltip is active */
    tooltipPlacement?: Placement;
    /** Dark variant, instead of default blue */
    dark?: boolean;
    /** Disables the default bold look of the link */
    thin?: boolean;
}>();

const emit = defineEmits<{
    (e: "click", event: PointerEvent): void;
}>();

function onClick(event: PointerEvent) {
    if (props.disabled) {
        event.preventDefault();
    } else {
        emit("click", event);
    }
}

const styleClasses = computed(() => {
    return {
        "g-dark": props.dark,
        "g-thin": props.thin,
        "g-disabled": props.disabled,
    };
});

const baseComponent = useClickableElement(props);
const currentTitle = useCurrentTitle(props);

const showTooltip = computed(() => props.tooltip && currentTitle.value);

const linkRef = ref<HTMLElement | InstanceType<typeof RouterLink> | null>(null);
const linkElementRef = useResolveElement(linkRef);
</script>

<template>
    <component
        :is="baseComponent"
        ref="linkRef"
        class="g-link"
        :class="styleClasses"
        :data-title="currentTitle"
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
            :reference="linkElementRef"
            :text="currentTitle"
            :placement="props.tooltipPlacement" />
    </component>
</template>

<style scoped lang="scss">
.g-link {
    border: none !important;
    background: none !important;
    padding: 0;
    color: var(--color-blue-600);
    display: inline;
    line-height: unset;
    vertical-align: unset;
    user-select: text;
    font-weight: bold;
    text-decoration: none;

    &:hover,
    &:focus,
    &:focus-visible {
        text-decoration: underline;
    }

    // bootstrap override
    &:focus,
    &:active:focus {
        box-shadow: none !important;
    }

    &:focus-visible {
        // this important is there because of bootstrap. todo: remove
        box-shadow: 0 0 0 0.2rem var(--color-blue-400) !important;
    }

    &.g-dark {
        color: var(--color-grey-700);
    }

    &.g-thin {
        font-weight: normal;
    }

    &.g-disabled {
        text-decoration: underline;
        color: var(--color-grey-500) !important;
        cursor: default;
    }
}
</style>
