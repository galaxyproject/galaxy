<script setup lang="ts">
import { ref, watch } from "vue";

const VegaWrapper = () => import("@/components/Common/VegaWrapper.vue");

const props = defineProps<{
    content: string;
}>();

const errorMessage = ref("");
const spec = ref({});

watch(
    () => props.content,
    () => {
        try {
            errorMessage.value = "";
            spec.value = {
                ...JSON.parse(props.content),
                width: "container",
            };
        } catch (e: any) {
            errorMessage.value = String(e);
            spec.value = {};
        }
    },
    { immediate: true }
);
</script>

<template>
    <b-alert v-if="errorMessage" class="p-2" variant="danger" show>
        {{ errorMessage }}
    </b-alert>
    <VegaWrapper v-else :spec="spec" />
</template>
