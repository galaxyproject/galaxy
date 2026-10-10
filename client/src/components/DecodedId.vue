<script setup lang="ts">
import { computed } from "vue";

import { useUserStore } from "@/stores/userStore";

const props = defineProps<{
    id: string;
}>();

const userStore = useUserStore();

const decodedId = computed<number | null>(() => userStore.getDecodedId(props.id));
</script>

<template>
    <span v-if="decodedId">({{ decodedId }})</span>
</template>
