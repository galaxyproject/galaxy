<script setup lang="ts">
/**
 * Dropdown menu item replacing BDropdownItem from bootstrap-vue.
 * Renders as a router-link, anchor, or button depending on props.
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
    emit("click", event);
    hideDropdown();
}

const tag = computed(() => {
    if (props.to) {
        return "router-link";
    }
    if (props.href) {
        return "a";
    }
    return "button";
});
</script>

<template>
    <component
        :is="tag"
        :class="classes"
        :to="to"
        :href="href"
        :target="target"
        :title="title"
        :disabled="disabled || undefined"
        :type="tag === 'button' ? 'button' : undefined"
        role="menuitem"
        @click="onClick">
        <slot />
    </component>
</template>
