<script setup lang="ts">
/**
 * Dropdown menu item replacing BDropdownItem from bootstrap-vue.
 * Renders as a router-link when `to` is provided, otherwise always renders as `<a>` (defaulting to
 * href="#") to match BDropdownItem's behavior. This is required for Selenium compatibility:
 * label-based selectors use By.LINK_TEXT which only finds <a> elements, and select_dropdown_item()
 * uses CSS selector "a.dropdown-item".
 * TODO: once Selenium selectors are updated, consider rendering action items as <button> (semantically
 * more correct for non-navigation actions).
 */

import { computed, inject } from "vue";

const props = withDefaults(
    defineProps<{
        /** Router link destination */
        to?: string | object;
        /** External link URL */
        href?: string;
        /** Link target (_blank, etc.) */
        target?: string;
        /** Active state */
        active?: boolean;
        /** Disabled state */
        disabled?: boolean;
        /** Color variant */
        variant?: string;
        /** Title/tooltip text */
        title?: string;
    }>(),
    {
        to: undefined,
        href: undefined,
        target: undefined,
        active: false,
        disabled: false,
        variant: undefined,
        title: undefined,
    },
);

const emit = defineEmits<{
    (e: "click", event: MouseEvent): void;
}>();

const hideDropdown = inject<() => void>("g-dropdown-hide", () => {});

const classes = computed(() => ({
    "dropdown-item": true,
    active: props.active,
    disabled: props.disabled,
    [`text-${props.variant}`]: !!props.variant,
}));

function onClick(event: MouseEvent) {
    if (props.disabled) {
        event.preventDefault();
        return;
    }
    // Prevent href="#" anchor navigation for action items
    if (!props.to) {
        event.preventDefault();
    }
    emit("click", event);
    hideDropdown();
}
</script>

<template>
    <router-link
        v-if="to"
        :class="classes"
        :to="to"
        :target="target"
        :title="title"
        :aria-disabled="disabled || undefined"
        role="menuitem"
        @click.native="onClick">
        <slot />
    </router-link>
    <a
        v-else
        :class="classes"
        :href="href ?? '#'"
        :target="target"
        :title="title"
        :aria-disabled="disabled || undefined"
        role="menuitem"
        @click="onClick">
        <slot />
    </a>
</template>

<style scoped>
.dropdown-item {
    cursor: pointer;
}
</style>
