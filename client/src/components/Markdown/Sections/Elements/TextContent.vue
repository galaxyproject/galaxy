<template>
    <pre class="m-0">{{ content }}</pre>
</template>

<script setup lang="ts">
defineProps<{
    content?: string;
}>();
</script>
