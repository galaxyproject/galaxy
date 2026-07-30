<script setup lang="ts">
/**
 * Form inside a dropdown menu, replacing BDropdownForm from bootstrap-vue.
 * The default padding stands in for bootstrap-vue's .b-dropdown-form; callers override it wholesale
 * rather than layering, since competing bootstrap spacing utilities are decided by stylesheet order
 * rather than by which one the caller passed.
 */

withDefaults(
    defineProps<{
        /** Padding/layout classes for the form element */
        formClass?: string;
    }>(),
    {
        formClass: "px-4 py-3",
    },
);
</script>

<template>
    <form :class="formClass" role="presentation" @click.stop @submit.prevent>
        <slot />
    </form>
</template>
