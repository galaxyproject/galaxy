<script setup lang="ts">
import { faCheck, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

interface Props {
    value?: boolean;
}

defineProps<Props>();
</script>

<template>
    <FontAwesomeIcon v-if="value" :icon="faCheck" />
    <FontAwesomeIcon v-else :icon="faTimes" />
</template>
