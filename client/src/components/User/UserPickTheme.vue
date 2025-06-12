<script setup lang="ts">
import { BModal } from "bootstrap-vue";

import ThemeSelector from "@/components/User/ThemeSelector.vue";

const emit = defineEmits<{
    (e: "reset"): void;
}>();
</script>

<template>
    <BModal id="pick-theme-modal" title="Pick a theme" size="lg" hide-footer centered visible @hidden="emit('reset')">
        Select a theme from the list below. The theme will be applied to the entire application.
        <ThemeSelector />
    </BModal>
</template>
