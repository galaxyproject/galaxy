<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { GDropdown } from "@galaxyproject/galaxy-ui"

defineProps<{
    /** Icon on the round toggle */
    icon: IconDefinition
    /** Accessible name of the toggle, which also names the menu */
    label: string
    /** Open upwards, for menus near the bottom of the page */
    dropup?: boolean
}>()
</script>

<template>
    <GDropdown
        class="action-menu"
        no-caret
        :dropup="dropup"
        :aria-label="label"
        toggle-class="action-menu-toggle"
        menu-class="action-menu-items"
    >
        <template #button-content>
            <FontAwesomeIcon :icon="icon" />
        </template>
        <slot />
    </GDropdown>
</template>

<style scoped lang="scss">
.action-menu {
    display: inline-block;
    margin-right: var(--spacing-2);

    :deep(.action-menu-toggle) {
        width: 2.5rem;
        height: 2.5rem;
        justify-content: center;
        padding: 0;
        border: none;
        border-radius: 50%;
        background-color: var(--color-grey-200);
        color: var(--color-galaxy-primary, #25537b);
        font-size: 1.1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);

        &:hover,
        &[aria-expanded="true"] {
            background-color: white;
        }
    }

    :deep(.action-menu-items) {
        box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.15);
    }

    // Icon and label in each item line up regardless of icon width
    :deep(.action-menu-items .dropdown-item) {
        display: flex;
        align-items: center;
        gap: var(--spacing-2);
    }
}
</style>
