<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
    vertical?: boolean;
}>();

const styleClasses = computed(() => {
    return {
        "g-vertical": props.vertical,
    };
});
</script>

<template>
    <div class="g-button-group" :class="styleClasses" role="group">
        <slot></slot>
    </div>
</template>

<style lang="scss" scoped>
.g-button-group {
    display: inline-flex;
    gap: 0;
    // Lines groups up with standalone buttons on the same text line
    vertical-align: middle;

    // A pressed button's darker border overlaps the next button's, so lift it; a focused button (z-index 999) stays on top
    &:deep(> .g-button.g-pressed:not(:focus)),
    &:deep(> :has(.g-button.g-pressed)) {
        z-index: 1;
    }

    // A focused GButton inside a wrapper is not a flex item, so lift the wrapper to keep its ring above the next button.
    &:deep(> :has(.g-button:focus-visible)) {
        z-index: 2;
    }

    // A group given a width (`w-100`) stretches its buttons instead of collapsing them to content width
    &:not(.g-vertical) {
        &:deep(> .g-button) {
            flex: 1 1 auto;
        }

        &:deep(> .g-button:not(:first-child)),
        &:deep(> :not(.g-button):not(:first-child) .g-button) {
            border-top-left-radius: 0;
            border-bottom-left-radius: 0;
        }

        &:deep(> .g-button:not(:last-child)),
        &:deep(> :not(.g-button):not(:last-child) .g-button) {
            border-top-right-radius: 0;
            border-bottom-right-radius: 0;
            // Width only: the shorthand would also reset the colour to currentcolor
            border-right-width: 0;
        }

        // Keeps the pressed button's own right border, drawn over the next button's left border
        &:deep(> .g-button.g-pressed:not(:last-child)),
        &:deep(> :not(.g-button):not(:last-child) .g-button.g-pressed) {
            margin-right: -1px;
            border-right-width: 1px;
        }
    }

    &.g-vertical {
        flex-direction: column;

        &:deep(> .g-button:not(:first-child)),
        &:deep(> :not(.g-button):not(:first-child) .g-button) {
            border-top-left-radius: 0;
            border-top-right-radius: 0;
        }

        &:deep(> .g-button:not(:last-child)),
        &:deep(> :not(.g-button):not(:last-child) .g-button) {
            border-bottom-left-radius: 0;
            border-bottom-right-radius: 0;
            border-bottom-width: 0;
        }

        // Keeps the pressed button's own bottom border, drawn over the next button's top border
        &:deep(> .g-button.g-pressed:not(:last-child)),
        &:deep(> :not(.g-button):not(:last-child) .g-button.g-pressed) {
            margin-bottom: -1px;
            border-bottom-width: 1px;
        }
    }
}
</style>
