<script setup lang="ts">
import GModal from "../BaseComponents/GModal.vue";
import ThemeSelector from "@/components/User/ThemeSelector.vue";

const emit = defineEmits<{
    (e: "reset"): void;
}>();
</script>

<template>
    <GModal id="pick-theme-modal" show title="Pick a theme" size="medium" @close="emit('reset')">
        Select a theme from the list below. The theme will be applied to the entire application.
        <ThemeSelector />
    </GModal>
</template>
