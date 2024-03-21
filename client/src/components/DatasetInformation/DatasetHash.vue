<script setup lang="ts">
interface Props {
    hash: {
        hash_value: string;
    };
}

defineProps<Props>();
</script>

<template>
    <li class="dataset-hash">
        <i>{{ hash.hash_value }}</i>
    </li>
</template>
