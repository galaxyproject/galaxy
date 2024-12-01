<script setup lang="ts">
defineProps<{
    content: string;
}>();
</script>

<template>
    <p class="text-justify m-2" v-html="content" />
</template>
