<script setup lang="ts">
import { faCheck, faTimes } from "@fortawesome/free-solid-svg-icons";

interface Props {
    value?: string;
}

defineProps<Props>();
</script>

<template>
    <icon v-if="value" :icon="faCheck" />
    <icon v-else :icon="faTimes" />
</template>
