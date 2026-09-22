<script setup lang="ts">
import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    action: string;
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "click"): void;
}>();
</script>

<template>
    <GButton color="blue" transparent @click="emit('click')"
        >I know what I am doing, force {{ action.toLowerCase() }}.</GButton
    >
</template>
