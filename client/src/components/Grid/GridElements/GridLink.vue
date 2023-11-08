<script setup lang="ts">
interface Props {
    text: string;
}
defineProps<Props>();
</script>

<template>
    <a class="font-weight-bold" href="#" @click.prevent="$emit('click')">{{ text }}</a>
</template>
