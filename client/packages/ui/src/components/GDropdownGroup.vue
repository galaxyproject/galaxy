<script setup lang="ts">
/**
 * Dropdown item group with optional header.
 * Replaces BDropdownGroup from bootstrap-vue.
 */

import { useUid } from "../composables/uid";

defineProps<{
    /** Group header text, which also names the group (a #header slot does not: it can hold a control) */
    header?: string;
    /** Extra CSS classes for the header element */
    headerClasses?: string | string[] | Record<string, boolean>;
}>();

const headerId = useUid("g-dropdown-group-header-");
</script>

<template>
    <div role="group" :aria-labelledby="header ? headerId : undefined">
        <!-- header like BDropdownGroup: an h6 has a tighter line height and cannot hold the block controls some headers do -->
        <header
            v-if="header || $slots.header"
            :id="headerId"
            class="dropdown-header"
            :class="headerClasses"
            role="presentation">
            <slot name="header">{{ header }}</slot>
        </header>
        <slot />
    </div>
</template>
