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
    <BButton variant="link" @click="emit('click')">我知道自己在做什么，强制 {{ action.toLowerCase() }}。</BButton>
</template>
