<script setup lang="ts">
/**
 * Alert component that renders a bootstrap-styled alert div.
 * Replaces bootstrap-vue's BAlert with a Vue 3-friendly SFC that emits the same
 * `<div class="alert alert-{variant}">` markup the existing bootstrap CSS expects.
 */

import { computed, ref, watch } from "vue";

type AlertVariant = "info" | "warning" | "danger" | "success" | "primary" | "secondary" | "light" | "dark";

interface Props {
    /** Controls alert visibility */
    show?: boolean;
    /** Bootstrap contextual variant */
    variant?: AlertVariant;
    /** Render a close button */
    dismissible?: boolean;
    /** Aria label for the dismiss button */
    dismissLabel?: string;
    /** Apply a fade transition on enter/leave */
    fade?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    show: true,
    variant: "info",
    dismissible: false,
    dismissLabel: "Close",
    fade: false,
});

const emit = defineEmits<{
    (e: "dismissed"): void;
    (e: "update:show", show: boolean): void;
}>();

const variantClass = computed(() => `alert-${props.variant}`);

// Mirror BAlert's localShow behavior so `dismissible` works without a parent
// handler -- the close button hides the alert locally, and a subsequent
// `show` prop change re-syncs.
const localShow = ref<boolean>(props.show);

watch(
    () => props.show,
    (next) => {
        localShow.value = next;
    },
);

function onDismiss() {
    localShow.value = false;
    emit("update:show", false);
    emit("dismissed");
}
</script>

<template>
    <Transition v-if="fade" name="g-alert-fade">
        <div
            v-if="localShow"
            class="alert"
            :class="[variantClass, { 'alert-dismissible': dismissible }]"
            role="alert"
            aria-live="polite"
            aria-atomic="true">
            <slot />
            <button v-if="dismissible" type="button" class="close" :aria-label="dismissLabel" @click="onDismiss">
                <span aria-hidden="true">&times;</span>
            </button>
        </div>
    </Transition>
    <div
        v-else-if="localShow"
        class="alert"
        :class="[variantClass, { 'alert-dismissible': dismissible }]"
        role="alert"
        aria-live="polite"
        aria-atomic="true">
        <slot />
        <button v-if="dismissible" type="button" class="close" :aria-label="dismissLabel" @click="onDismiss">
            <span aria-hidden="true">&times;</span>
        </button>
    </div>
</template>

<style scoped lang="scss">
.g-alert-fade-enter-active,
.g-alert-fade-leave-active {
    transition: opacity 0.15s linear;
}
.g-alert-fade-enter,
.g-alert-fade-enter-from,
.g-alert-fade-leave-to {
    opacity: 0;
}
</style>
