<template>
    <ConfigureGalaxy
        v-if="name === 'galaxy'"
        :content="content"
        @change="$emit('change', $event)"
        @cancel="$emit('cancel')" />
    <b-alert v-else variant="warning" show> Data cannot be linked to this cell type. </b-alert>
</template>

<script setup lang="ts">
import ConfigureGalaxy from "./Configurations/ConfigureGalaxy.vue";

defineProps<{
    name: string;
    content: string;
}>();

defineEmits<{
    (e: "cancel"): void;
    (e: "change", content: string): void;
}>();
</script>
