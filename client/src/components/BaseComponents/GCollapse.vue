<script setup lang="ts">
/**
 * Collapsible content container with animated height transition.
 * Replaces bootstrap-vue's BCollapse for regular (non-navbar) usage.
 *
 * Supports both one-way `:visible` prop and two-way `v-model` binding.
 * Accordion groups ensure only one collapse is open at a time.
 */

import { computed, onBeforeUnmount, ref, watch } from "vue";

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

function close() {
    internalOpen.value = false;
    emit("input", false);
}

watch(isOpen, (newVal, oldVal) => {
    if (newVal === oldVal) {
        return;
    }
    if (newVal) {
        emit("show");
        if (props.accordion) {
            const existing = accordionRegistry.get(props.accordion);
            if (existing && existing !== close) {
                existing();
            }
            accordionRegistry.set(props.accordion, close);
        }
    } else {
        emit("hide");
    }
});

function onTransitionEnd() {
    if (isOpen.value) {
        emit("shown");
        // After opening transition completes, allow content to reflow naturally
        if (contentRef.value) {
            contentRef.value.style.maxHeight = "none";
        }
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
            el.style.maxHeight = el.scrollHeight + "px";
        } else {
            // Force a reflow so the transition starts from the current height
            el.style.maxHeight = el.scrollHeight + "px";
            // eslint-disable-next-line no-unused-expressions
            el.offsetHeight;
            el.style.maxHeight = "0";
        }
    },
    { flush: "post" },
);

onBeforeUnmount(() => {
    if (props.accordion && accordionRegistry.get(props.accordion) === close) {
        accordionRegistry.delete(props.accordion);
    }
});
</script>

<template>
    <div
        ref="contentRef"
        class="g-collapse"
        :class="{ 'g-collapse-open': isOpen }"
        :style="{ maxHeight: isOpen ? undefined : '0px' }"
        role="region"
        @transitionend="onTransitionEnd">
        <slot />
    </div>
</template>

<style scoped>
.g-collapse {
    overflow: hidden;
    transition: max-height 0.3s ease;
}

.g-collapse-open {
    overflow: visible;
}
</style>
