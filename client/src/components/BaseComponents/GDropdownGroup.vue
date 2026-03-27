<script setup lang="ts">
/**
 * Dropdown item group with optional header.
 * Replaces BDropdownGroup from bootstrap-vue.
 */

defineProps<{
    /** Group header text (or use #header slot) */
    header?: string;
    /** Extra CSS classes for the header element */
    headerClasses?: string | string[] | Record<string, boolean>;
}>();
</script>

<template>
    <div role="group">
        <h6 v-if="header || $slots.header" class="dropdown-header" :class="headerClasses" role="presentation">
            <slot name="header">{{ header }}</slot>
        </h6>
        <slot />
    </div>
</template>
