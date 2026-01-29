<script setup lang="ts">
interface Props {
    contents: string
}

defineProps<Props>()
</script>

<template>
    <pre style="border-left: 1px solid gray; padding-left: 10px">{{ contents }}</pre>
</template>
