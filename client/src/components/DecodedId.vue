<script setup lang="ts">
import { storeToRefs } from "pinia";
import { ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { useUserStore } from "@/stores/userStore";

const props = defineProps<{
    id: string;
}>();

const { isAdmin } = storeToRefs(useUserStore());

const decodedId = ref<number | null>(null);

watch(
    () => props.id,
    async (newId) => {
        decodedId.value = null;
        if (isAdmin.value) {
            const { data, error } = await GalaxyApi().GET("/api/configuration/decode/{encoded_id}", {
                params: {
                    path: { encoded_id: newId },
                },
            });
            if (error) {
                console.error(error);
                decodedId.value = null;
            } else {
                decodedId.value = data?.decoded_id || null;
            }
        }
    },
    { immediate: true },
);
</script>

<template>
    <span v-if="decodedId">({{ decodedId }})</span>
</template>
