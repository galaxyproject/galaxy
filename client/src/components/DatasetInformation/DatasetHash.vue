<script setup lang="ts">
import { type DatasetHash } from "@/api";

interface Props {
    hash: DatasetHash;
}

defineProps<Props>();
</script>

<template>
    <li class="dataset-hash">
        <i>{{ hash.hash_value }}</i>
    </li>
</template>
