<script setup lang="ts">
/**
 * Collapsible content container with animated height transition.
 * Replaces bootstrap-vue's BCollapse for regular (non-navbar) usage.
 *
 * Uses the same transition approach as Bootstrap: animates the `height`
 * property and hides with `display: none` when fully collapsed.
 *
 * Supports both one-way `:visible` prop and two-way `v-model` binding.
 * Accordion groups ensure only one collapse is open at a time.
 */

import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

// Module-level accordion registry: maps group name to the close callback of the currently open member
const accordionRegistry = new Map<string, () => void>();

const props = withDefaults(
    defineProps<{
        /** Two-way binding for open/closed state (v-model) */
        value?: boolean;
        /** One-way visibility control */
        visible?: boolean;
        /** Accordion group name — only one in the group can be open */
        accordion?: string;
    }>(),
    {
        value: undefined,
        visible: undefined,
        accordion: undefined,
    },
);

const emit = defineEmits<{
    (e: "input", value: boolean): void;
    (e: "show"): void;
    (e: "shown"): void;
    (e: "hide"): void;
    (e: "hidden"): void;
}>();

const contentRef = ref<HTMLElement | null>(null);
const internalOpen = ref(false);
const transitioning = ref(false);

const isOpen = computed(() => {
    if (props.value !== undefined) {
        return props.value;
    }
    if (props.visible !== undefined) {
        return props.visible;
    }
    return internalOpen.value;
});

function closeSelf() {
    internalOpen.value = false;
    emit("input", false);
}

onMounted(() => {
    if (isOpen.value && props.accordion) {
        accordionRegistry.set(props.accordion, closeSelf);
    }
});

function onTransitionEnd(e: TransitionEvent) {
    const el = contentRef.value;
    if (!el || e.target !== el) {
        return;
    }
    if (isOpen.value) {
        el.style.height = "";
        transitioning.value = false;
        emit("shown");
    } else {
        transitioning.value = false;
        emit("hidden");
    }
}

// Pre-flush watcher: set transitioning BEFORE the DOM update so class
// bindings include .g-collapsing (which keeps the element visible during
// the close animation instead of jumping to display:none).
watch(isOpen, () => {
    transitioning.value = true;
});

// Post-flush watcher: run the animation AFTER Vue has applied the new classes.
watch(
    isOpen,
    (open) => {
        const el = contentRef.value;
        if (!el) {
            return;
        }
        if (open) {
            emit("show");
            if (props.accordion) {
                const existing = accordionRegistry.get(props.accordion);
                if (existing && existing !== closeSelf) {
                    existing();
                }
                accordionRegistry.set(props.accordion, closeSelf);
            }
            el.style.height = "0px";
            el.offsetHeight; // force reflow
            el.style.height = el.scrollHeight + "px";
        } else {
            emit("hide");
            el.style.height = el.offsetHeight + "px";
            el.offsetHeight; // force reflow
            el.style.height = "0px";
        }
    },
    { flush: "post" },
);

onBeforeUnmount(() => {
    if (props.accordion && accordionRegistry.get(props.accordion) === closeSelf) {
        accordionRegistry.delete(props.accordion);
    }
});
</script>

<template>
    <div
        ref="contentRef"
        class="g-collapse"
        :class="{
            'g-collapse-open': isOpen,
            'g-collapse-hidden': !isOpen && !transitioning,
            'g-collapsing': transitioning,
        }"
        @transitionend="onTransitionEnd">
        <slot />
    </div>
</template>

<style scoped>
.g-collapse-hidden {
    display: none;
}
.g-collapsing {
    position: relative;
    overflow: hidden;
    transition: height 0.35s ease;
}
</style>
