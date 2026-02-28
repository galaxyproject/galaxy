<script setup lang="ts">
/**
 * Dropdown item group with optional header.
 * Replaces BDropdownGroup from bootstrap-vue.
 */

defineProps<{
    /** Group header text (or use #header slot) */
    header?: string;
}>();
</script>

<template>
    <div role="group">
        <h6 v-if="header || $slots.header" class="dropdown-header" role="presentation">
            <slot name="header">{{ header }}</slot>
        </h6>
        <slot />
    </div>
</template>
