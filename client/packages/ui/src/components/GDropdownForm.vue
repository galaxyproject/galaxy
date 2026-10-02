<script setup lang="ts">
/** Replaces BDropdownForm. formClass replaces the default padding, as clashing spacing utilities win by CSS order. */

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
