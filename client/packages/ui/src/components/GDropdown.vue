<script setup lang="ts">
/**
 * Dropdown component replacing BDropdown from bootstrap-vue.
 * Uses Bootstrap 4 CSS classes for styling, native DOM for click-outside.
 * Supports toggle text/slot, right-aligned menus, sizes, variants,
 * split buttons, dropup, no-caret, and menu/toggle class customization.
 * Keyboard support follows the WAI-ARIA APG menu button pattern.
 */

import { autoUpdate, computePosition, flip, offset, type Placement, shift } from "@floating-ui/dom";
import { computed, nextTick, onBeforeUnmount, provide, ref, watch } from "vue";

import { useUid } from "../composables/uid";
import { dropdownHideKey } from "./dropdownContext";

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
        /** Accessible name of the toggle, which also names the menu; for toggles without visible text */
        ariaLabel?: string;
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
        ariaLabel: undefined,
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
let unmounted = false;
let stopAutoUpdate: (() => void) | undefined;
/** Settles once the opened menu has its first position */
let menuPositioned: Promise<void> = Promise.resolve();

const uid = useUid("g-dropdown-");
const splitButtonId = computed(() => `${uid.value}-button`);
const toggleId = computed(() => `${uid.value}-toggle`);
const menuId = computed(() => `${uid.value}-menu`);

// Bound only when set: Vue 2 strips an attribute bound to undefined on every render, dropping v-g-tooltip's label
const toggleLabelAttrs = computed(() => (props.ariaLabel ? { "aria-label": props.ariaLabel } : {}));

const menuPlacement = computed<Placement>(() => {
    if (props.dropup) {
        return props.right ? "top-end" : "top-start";
    }
    if (props.dropright) {
        return "right-start";
    }
    if (props.dropleft) {
        return "left-start";
    }
    return props.right ? "bottom-end" : "bottom-start";
});

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
    menuPositioned = nextTick().then(() => {
        // An unmount before this tick has already removed the listeners
        if (isOpen.value && !unmounted) {
            document.addEventListener("click", onOutsideEvent, true);
            document.addEventListener("focusin", onOutsideEvent, true);
            return startPositioning();
        }
    });
}

/** The same reference element as BDropdown: the whole group for split buttons and right-aligned dropups */
function getMenuReference() {
    return props.split || (props.dropup && props.right) ? dropdownEl.value : toggleEl.value;
}

async function positionMenu() {
    const reference = getMenuReference();
    const menu = menuEl.value;
    if (!reference || !menu) {
        return;
    }
    // Flip and shift keep the menu inside its scroll container and the viewport, with Popper's 5px padding
    const { x, y } = await computePosition(reference, menu, {
        placement: menuPlacement.value,
        middleware: [offset(2), flip({ padding: 5 }), shift({ padding: 5 })],
    });
    // Replaces Bootstrap's static offsets and its 2px spacer margin, which offset() stands in for
    Object.assign(menu.style, { top: `${y}px`, left: `${x}px`, right: "auto", bottom: "auto", margin: "0" });
}

function startPositioning() {
    // show(), hide() and show() in one tick start twice
    stopPositioning();
    const reference = getMenuReference();
    const menu = menuEl.value;
    if (!reference || !menu) {
        return;
    }
    // Resolves on the first update, which autoUpdate runs right away
    return new Promise<void>((resolve) => {
        stopAutoUpdate = autoUpdate(reference, menu, () => positionMenu().then(resolve));
    });
}

function stopPositioning() {
    stopAutoUpdate?.();
    stopAutoUpdate = undefined;
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
    stopPositioning();
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
    // Focus scrolls to the item, so it waits for the menu to be placed and possibly flipped
    await menuPositioned;
    if (isOpen.value) {
        focusMenuItem(index);
    }
}

function onToggleClick(event: MouseEvent) {
    toggle(event);
    // Clicks synthesized from Enter/Space have no click count
    if (isOpen.value && event.detail === 0) {
        openAndFocusMenuItem(0);
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

    // Enter on an item, and Enter or Space on the toggle, activate natively: only keep them from ancestors
    const activatesNatively = event.key === "Enter" ? onMenuItem || onToggle : event.key === " " && onToggle;
    if (handled || activatesNatively) {
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
provide(dropdownHideKey, hide);

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

// The disabled toggle could no longer close it
watch(
    () => props.disabled,
    (disabled) => {
        if (disabled) {
            hide(false);
        }
    },
);

onBeforeUnmount(() => {
    unmounted = true;
    removeOutsideListeners();
    stopPositioning();
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
            :id="splitButtonId"
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
            v-bind="toggleLabelAttrs"
            @click="onToggleClick"
            @keydown="onKeydown">
            <template v-if="!split">
                <slot name="button-content">{{ text }}</slot>
            </template>
            <span v-if="split" class="sr-only">{{ text ? `More options for ${text}` : "More options" }}</span>
        </button>

        <!-- Dropdown menu -->
        <!-- Focusable like BDropdown's menu, which Selenium sends keys to -->
        <div
            v-if="shouldRenderMenu"
            :id="menuId"
            ref="menuEl"
            tabindex="-1"
            role="menu"
            :class="menuClasses"
            :aria-labelledby="split ? splitButtonId : toggleId"
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
