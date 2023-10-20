<script setup lang="ts">
interface Props {
    text: string;
}
defineProps<Props>();
</script>

<template>
    <span>{{ text }}</span>
</template>
