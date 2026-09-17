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

    // Matches Bootstrap's `.btn-group > .btn`, so a group given a width (`w-100`)
    // stretches its buttons instead of collapsing them to content width.
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
            border-right: 0;
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
            border-bottom: 0;
        }
    }
}
</style>
