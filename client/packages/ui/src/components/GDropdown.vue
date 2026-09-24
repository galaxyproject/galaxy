<script setup lang="ts">
/**
 * Dropdown component replacing BDropdown from bootstrap-vue.
 * Uses Bootstrap 4 CSS classes for styling, native DOM for click-outside.
 * Supports toggle text/slot, right-aligned menus, sizes, variants,
 * split buttons, dropup, no-caret, and menu/toggle class customization.
 * Keyboard support follows the WAI-ARIA APG menu button pattern.
 */

import { computed, nextTick, onBeforeUnmount, provide, ref } from "vue";

import { useUid } from "../composables/uid";

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
        /** Disabled state */
        disabled?: boolean;
        /** Lazy render menu content */
        lazy?: boolean;
    }>(),
    {
        text: undefined,
        variant: "secondary",
        size: undefined,
        right: false,
        noCaret: false,
        dropup: false,
        dropleft: false,
        dropright: false,
        block: false,
        split: false,
        toggleClass: undefined,
        menuClass: undefined,
        disabled: false,
        lazy: false,
    },
);

const emit = defineEmits<{
    (e: "show"): void;
    (e: "hide"): void;
    (e: "click", event: MouseEvent): void;
}>();

const isOpen = ref(false);
const dropdownEl = ref<HTMLDivElement>();
const toggleEl = ref<HTMLButtonElement>();
const menuEl = ref<HTMLDivElement>();
const hasBeenOpened = ref(false);

const uid = useUid("g-dropdown-");
const toggleId = computed(() => `${uid.value}-toggle`);
const menuId = computed(() => `${uid.value}-menu`);

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
        if (isOpen.value) {
            document.addEventListener("click", onOutsideEvent, true);
            document.addEventListener("focusin", onOutsideEvent, true);
        }
    });
}

function removeOutsideListeners() {
    document.removeEventListener("click", onOutsideEvent, true);
    document.removeEventListener("focusin", onOutsideEvent, true);
}

function hide(restoreFocus = true) {
    if (!isOpen.value) {
        return;
    }
    // Focus would otherwise be lost to the page once the menu holding it is hidden
    const focusInMenu = !!menuEl.value?.contains(document.activeElement);
    isOpen.value = false;
    emit("hide");
    removeOutsideListeners();
    if (restoreFocus && focusInMenu) {
        toggleEl.value?.focus();
    }
}

function onOutsideEvent(event: Event) {
    if (dropdownEl.value && !dropdownEl.value.contains(event.target as Node)) {
        hide(false);
    }
}

function ownsMenuItem(element: HTMLElement) {
    // Items of a nested dropdown belong to its menu, which handles its own keys
    return element.closest('[role="menu"]') === menuEl.value;
}

function getMenuItems() {
    const selector = '[role="menuitem"]:not([disabled]):not([aria-disabled="true"])';
    return Array.from(menuEl.value?.querySelectorAll<HTMLElement>(selector) ?? []).filter(ownsMenuItem);
}

/** Focuses the item at `index`, wrapping around at both ends; -1 is the last item. */
function focusMenuItem(index: number) {
    const items = getMenuItems();
    if (items.length) {
        items[(index + items.length) % items.length]?.focus();
    }
}

async function openAndFocusMenuItem(index: number) {
    show();
    await nextTick();
    focusMenuItem(index);
}

function onToggleClick(event: MouseEvent) {
    toggle(event);
    // Clicks synthesized from Enter/Space have no click count
    if (isOpen.value && event.detail === 0) {
        nextTick(() => focusMenuItem(0));
    }
}

function onKeydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement;
    const onToggle = target === toggleEl.value;
    const onMenuItem = target.getAttribute("role") === "menuitem" && ownsMenuItem(target);
    const inMenuNavigation = onMenuItem || target === menuEl.value;
    let handled = true;

    if (event.key === "ArrowDown" && onToggle) {
        openAndFocusMenuItem(0);
    } else if (event.key === "ArrowUp" && onToggle) {
        openAndFocusMenuItem(-1);
    } else if (event.key === "ArrowDown" && inMenuNavigation) {
        focusMenuItem(getMenuItems().indexOf(target) + 1);
    } else if (event.key === "ArrowUp" && inMenuNavigation) {
        focusMenuItem(Math.max(getMenuItems().indexOf(target), 0) - 1);
    } else if ((event.key === "Home" || event.key === "End") && inMenuNavigation) {
        focusMenuItem(event.key === "Home" ? 0 : -1);
    } else if (event.key === "Escape" && isOpen.value) {
        hide();
    } else if (event.key === " " && onMenuItem) {
        // Space does not activate links natively
        target.click();
    } else {
        handled = false;
    }

    // Enter activates the item natively, so only keep it from ancestors
    if (handled || (event.key === "Enter" && onMenuItem)) {
        // Bootstrap's document-level keydown handler would refocus the item, and GCard would take Space as a click
        event.stopPropagation();
    }
    if (handled) {
        event.preventDefault();
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

onBeforeUnmount(() => {
    removeOutsideListeners();
});

defineExpose({
    show,
    hide,
    toggle,
});
</script>

<template>
    <div ref="dropdownEl" :class="containerClasses">
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
            :id="toggleId"
            ref="toggleEl"
            type="button"
            class="btn"
            :class="toggleBtnClasses"
            :disabled="disabled"
            aria-haspopup="menu"
            :aria-expanded="isOpen ? 'true' : 'false'"
            :aria-controls="shouldRenderMenu ? menuId : undefined"
            @click="onToggleClick"
            @keydown="onKeydown">
            <template v-if="!split">
                <slot name="button-content">{{ text }}</slot>
            </template>
            <span v-if="split" class="sr-only">Toggle Dropdown</span>
        </button>

        <!-- Dropdown menu -->
        <!-- tabindex="-1" matches BDropdown behavior and allows send_keys/send_escape in Selenium tests -->
        <div
            v-if="shouldRenderMenu"
            :id="menuId"
            ref="menuEl"
            tabindex="-1"
            role="menu"
            :class="menuClasses"
            :aria-labelledby="toggleId"
            @keydown="onKeydown">
            <slot />
        </div>
    </div>
</template>

<style scoped lang="scss">
.dropdown-toggle-no-caret::after {
    display: none !important;
}

// Bootstrap's translucent focus shadow is below 3:1 against white
.dropdown-toggle:focus-visible {
    outline: 2px solid var(--color-blue-600);
    outline-offset: 2px;
}
</style>
