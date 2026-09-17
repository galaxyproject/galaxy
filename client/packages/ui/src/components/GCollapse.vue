<script setup lang="ts">
/**
 * Collapsible content container with animated height transition.
 * Replaces bootstrap-vue's BCollapse for regular (non-navbar) usage.
 *
 * Uses height: 0 / overflow: hidden for the closed state so scrollHeight
 * is always readable (unlike display: none which returns 0).
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
// Stays true during close animation so slot content can remain mounted
const contentActive = ref(false);

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

// Sync: set contentActive true immediately so slot renders before post-flush animation
watch(
    isOpen,
    (open) => {
        if (open) {
            contentActive.value = true;
        }
    },
    { flush: "sync" },
);

onMounted(() => {
    const el = contentRef.value;
    if (isOpen.value) {
        contentActive.value = true;
        if (el) {
            el.style.height = "auto";
            el.style.overflow = "visible";
        }
        if (props.accordion) {
            accordionRegistry.set(props.accordion, closeSelf);
        }
    } else if (el) {
        el.style.display = "none";
    }
});

function onTransitionEnd(e: TransitionEvent) {
    const el = contentRef.value;
    if (!el || e.target !== el) {
        return;
    }
    if (isOpen.value) {
        el.style.height = "auto";
        el.style.overflow = "visible";
        emit("shown");
    } else {
        el.style.display = "none";
        el.style.height = "";
        el.style.overflow = "";
        contentActive.value = false;
        emit("hidden");
    }
}

// Post-flush: run animations after DOM updates
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
            // Switch from display:none to height:0/overflow:hidden so
            // scrollHeight is readable, then animate to full height.
            el.style.display = "";
            el.style.overflow = "hidden";
            el.style.height = "0px";
            requestAnimationFrame(() => {
                el.style.height = el.scrollHeight + "px";
            });
        } else {
            emit("hide");
            // Closing: start from current height, animate to 0
            el.style.overflow = "hidden";
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
    <div ref="contentRef" class="g-collapse" :class="{ 'g-collapse-open': isOpen }" @transitionend="onTransitionEnd">
        <slot :content-active="contentActive" />
    </div>
</template>

<style scoped>
.g-collapse {
    height: 0;
    overflow: hidden;
    transition: height 0.35s ease;
}
</style>
