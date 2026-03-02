<script setup lang="ts">
/**
 * Collapsible content container with animated height transition.
 * Replaces bootstrap-vue's BCollapse for regular (non-navbar) usage.
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
    const el = contentRef.value;
    if (!el) {
        return;
    }
    if (isOpen.value) {
        // Already open on mount — show at full height without animating
        el.style.maxHeight = "";
        el.style.overflow = "";
    }
    // If closed, the CSS max-height: 0 handles initial state
});

function onTransitionEnd() {
    const el = contentRef.value;
    if (!el) {
        return;
    }
    if (isOpen.value) {
        // Release height constraint so dynamic content can grow after opening
        el.style.maxHeight = "";
        el.style.overflow = "";
        emit("shown");
    } else {
        emit("hidden");
    }
}

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
            // Keep overflow hidden during animation so content doesn't escape the container
            el.style.overflow = "hidden";
            // Explicitly start from 0 so the transition always plays from the closed position
            el.style.maxHeight = "0";
            el.offsetHeight; // force reflow to commit the 0 before transitioning to target height
            el.style.maxHeight = el.scrollHeight + "px";
        } else {
            emit("hide");
            el.style.overflow = "hidden";
            // Explicitly set current height so the transition has a defined start point
            el.style.maxHeight = el.scrollHeight + "px";
            el.offsetHeight; // force reflow
            el.style.maxHeight = "0";
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
    <div ref="contentRef" class="g-collapse" :class="{ 'g-collapse-open': isOpen }" @transitionend="onTransitionEnd">
        <slot />
    </div>
</template>

<style scoped>
.g-collapse {
    overflow: hidden;
    max-height: 0;
    transition: max-height 0.35s ease;
}
</style>
