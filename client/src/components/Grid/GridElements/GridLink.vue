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
    <button class="ui-link font-weight-bold" @click="emit('click')">{{ text }}</button>
</template>
