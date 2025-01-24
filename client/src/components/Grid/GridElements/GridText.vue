<script setup lang="ts">
interface Props {
    text?: string | number;
}
defineProps<Props>();
</script>

<template>
    <span v-localize>{{ text ?? "-" }}</span>
</template>
