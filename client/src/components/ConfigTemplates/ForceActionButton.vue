<script setup lang="ts">
import { BButton } from "bootstrap-vue";

interface Props {
    action: string;
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "click"): void;
}>();
</script>

<template>
    <BButton variant="link" @click="emit('click')">I know what I am doing, force {{ action.toLowerCase() }}.</BButton>
</template>
