<script setup lang="ts">
import { BAlert } from "bootstrap-vue";

interface Props {
    jaggedDataWarning?: string;
}

defineProps<Props>();
</script>

<template>
    <span>
        <BAlert v-if="jaggedDataWarning" show variant="warning">
            {{ jaggedDataWarning }}
        </BAlert>
    </span>
</template>
