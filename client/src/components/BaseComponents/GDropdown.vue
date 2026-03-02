<script setup lang="ts">
/**
 * Dropdown component replacing BDropdown from bootstrap-vue.
 * Uses Bootstrap 4 CSS classes for styling, native DOM for click-outside.
 * Supports toggle text/slot, right-aligned menus, sizes, variants,
 * split buttons, dropup, no-caret, and menu/toggle class customization.
 */

import { computed, nextTick, onBeforeUnmount, onMounted, provide, ref } from "vue";

const props = withDefaults(
    defineProps<{
        /** Text for the toggle button */
        text?: string;
        /** Button variant (primary, secondary, link, info, etc.) */
        variant?: string;
        /** Button size (sm, lg) */
        size?: string;
        /** Align dropdown menu to the right */
        right?: boolean;
        /** Hide the caret icon */
        noCaret?: boolean;
        /** Prevent menu from flipping */
        noFlip?: boolean;
        /** Drop direction */
        dropup?: boolean;
        dropleft?: boolean;
        dropright?: boolean;
        /** Full-width block style */
        block?: boolean;
        /** Split button mode */
        split?: boolean;
        /** Extra classes for the toggle button */
        toggleClass?: string | string[] | Record<string, boolean>;
        /** Extra classes for the dropdown menu */
        menuClass?: string | string[] | Record<string, boolean>;
        /** Boundary for positioning */
        boundary?: string;
        /** Disabled state */
        disabled?: boolean;
        /** ARIA role */
        role?: string;
        /** Lazy render menu content */
        lazy?: boolean;
        /** Offset */
        offset?: number | string;
    }>(),
    {
        text: undefined,
        variant: "secondary",
        size: undefined,
        right: false,
        noCaret: false,
        noFlip: false,
        dropup: false,
        dropleft: false,
        dropright: false,
        block: false,
        split: false,
        toggleClass: undefined,
        menuClass: undefined,
        boundary: undefined,
        disabled: false,
        role: undefined,
        lazy: false,
        offset: undefined,
    },
);

const emit = defineEmits<{
    (e: "show"): void;
    (e: "hide"): void;
    (e: "click", event: MouseEvent): void;
}>();

const isOpen = ref(false);
const dropdownEl = ref<HTMLDivElement>();
const menuEl = ref<HTMLDivElement>();
const hasBeenOpened = ref(false);

function toggle(event?: MouseEvent) {
    if (props.disabled) {
        return;
    }
    if (isOpen.value) {
        hide();
    } else {
        show();
    }
    if (event) {
        event.stopPropagation();
    }
}

function show() {
    if (props.disabled || isOpen.value) {
        return;
    }
    isOpen.value = true;
    hasBeenOpened.value = true;
    emit("show");
    nextTick(() => {
        document.addEventListener("click", onClickOutside, true);
    });
}

function hide() {
    if (!isOpen.value) {
        return;
    }
    isOpen.value = false;
    emit("hide");
    document.removeEventListener("click", onClickOutside, true);
}

function onClickOutside(event: Event) {
    if (dropdownEl.value && !dropdownEl.value.contains(event.target as Node)) {
        hide();
    }
}

function onSplitClick(event: MouseEvent) {
    emit("click", event);
}

// Provide hide function to child items so they can close the menu on click
provide("g-dropdown-hide", hide);

const containerClasses = computed(() => ({
    "btn-group": !props.block,
    dropdown: !props.dropup && !props.dropleft && !props.dropright,
    dropup: props.dropup,
    dropleft: props.dropleft,
    dropright: props.dropright,
    show: isOpen.value,
    "d-flex": props.block,
}));

const toggleBtnClasses = computed(() => {
    const classes: (string | string[] | Record<string, boolean>)[] = ["dropdown-toggle", `btn-${props.variant}`];
    if (props.size) {
        classes.push(`btn-${props.size}`);
    }
    if (props.noCaret) {
        classes.push("dropdown-toggle-no-caret");
    }
    if (props.split) {
        classes.push("dropdown-toggle-split");
    }
    if (props.block) {
        classes.push("flex-grow-1");
    }
    if (props.toggleClass) {
        classes.push(props.toggleClass);
    }
    return classes;
});

const menuClasses = computed(() => {
    const classes: (string | string[] | Record<string, boolean>)[] = ["dropdown-menu"];
    if (isOpen.value) {
        classes.push("show");
    }
    if (props.right) {
        classes.push("dropdown-menu-right");
    }
    if (props.menuClass) {
        classes.push(props.menuClass);
    }
    return classes;
});

const shouldRenderMenu = computed(() => {
    if (!props.lazy) {
        return true;
    }
    return hasBeenOpened.value;
});

onMounted(() => {
    // Clean up on mount if needed
});

onBeforeUnmount(() => {
    document.removeEventListener("click", onClickOutside, true);
});

defineExpose({
    show,
    hide,
    toggle,
});
</script>

<template>
    <div ref="dropdownEl" :class="containerClasses" :role="role">
        <!-- Split button: action button + toggle -->
        <button
            v-if="split"
            type="button"
            class="btn"
            :class="[`btn-${variant}`, size ? `btn-${size}` : '']"
            :disabled="disabled"
            @click="onSplitClick">
            <slot name="button-content">{{ text }}</slot>
        </button>

        <!-- Toggle button -->
        <button
            type="button"
            class="btn"
            :class="toggleBtnClasses"
            :disabled="disabled"
            aria-haspopup="true"
            :aria-expanded="isOpen"
            @click="toggle">
            <template v-if="!split">
                <slot name="button-content">{{ text }}</slot>
            </template>
            <span v-if="split" class="sr-only">Toggle Dropdown</span>
        </button>

        <!-- Dropdown menu -->
        <!-- tabindex="-1" matches BDropdown behavior and allows send_keys/send_escape in Selenium tests -->
        <div
            v-if="shouldRenderMenu"
            ref="menuEl"
            tabindex="-1"
            :class="menuClasses"
            :role="role === 'menu' ? 'menu' : undefined"
            @keydown.esc="hide">
            <slot />
        </div>
    </div>
</template>

<style scoped lang="scss">
.dropdown-toggle-no-caret::after {
    display: none !important;
}
</style>
