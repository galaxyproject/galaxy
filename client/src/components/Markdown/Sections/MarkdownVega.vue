<script setup lang="ts">
import { ref, watch } from "vue";

import GAlert from "@/components/BaseComponents/GAlert.vue";

const VegaWrapper = () => import("@/components/Common/VegaWrapper.vue");

const props = defineProps<{
    content: string;
}>();

const errorMessage = ref("");
const spec = ref({});

function render() {
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
}

watch(
    () => props.content,
    () => {
        render();
    },
    { immediate: true },
);
</script>

<template>
    <div>
        <GAlert v-if="errorMessage" class="p-2" variant="danger" show>
            {{ errorMessage }}
        </GAlert>
        <VegaWrapper :spec="spec" />
    </div>
</template>
