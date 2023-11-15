<script setup lang="ts">
interface Props {
    text?: string;
}
defineProps<Props>();
</script>

<template>
    <span v-localize>{{ text ?? "Not available." }}</span>
</template>
