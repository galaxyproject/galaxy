<script setup lang="ts">
interface Props {
    info?: string;
}

defineProps<Props>();
</script>

<template>
    <div>
        {{ info }}
    </div>
</template>
