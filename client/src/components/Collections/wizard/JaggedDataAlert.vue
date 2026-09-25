<script setup lang="ts">
import GAlert from "@/components/BaseComponents/GAlert.vue";

interface Props {
    jaggedDataWarning?: string;
}

defineProps<Props>();
</script>

<template>
    <span>
        <GAlert v-if="jaggedDataWarning" show variant="warning">
            {{ jaggedDataWarning }}
        </GAlert>
    </span>
</template>
