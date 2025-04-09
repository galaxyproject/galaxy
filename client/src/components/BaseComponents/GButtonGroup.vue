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
    <div class="g-button-group" :class="styleClasses">
        <slot></slot>
    </div>
</template>

<style lang="scss" scoped>
.g-button-group {
    display: inline-flex;
    gap: 0;

    &:not(.g-vertical) {
        &:deep(.g-button) {
            &:not(:nth-child(1 of .g-button)) {
                border-top-left-radius: 0;
                border-bottom-left-radius: 0;
            }

            &:not(:nth-last-child(1 of .g-button)) {
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;

                border-right: 0;
            }
        }
    }

    &.g-vertical {
        flex-direction: column;

        &:deep(.g-button) {
            &:not(:nth-child(1 of .g-button)) {
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }

            &:not(:nth-last-child(1 of .g-button)) {
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;

                border-bottom: 0;
            }
        }
    }
}
</style>
