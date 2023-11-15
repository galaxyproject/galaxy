<script setup lang="ts">
interface Props {
    text: string;
}
defineProps<Props>();
const emit = defineEmits<{
    (e: "click"): void;
}>();
</script>

<template>
    <a class="font-weight-bold" href="#" @click.prevent="$emit('click')">{{ text }}</a>
</template>
