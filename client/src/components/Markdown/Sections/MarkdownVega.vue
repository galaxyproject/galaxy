<script setup lang="ts">
import { ref, watch } from "vue";

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
    { immediate: true }
);
</script>

<template>
    <div>
        <b-alert v-if="errorMessage" class="p-2" variant="danger" show>
            {{ errorMessage }}
        </b-alert>
        <VegaWrapper :spec="spec" />
    </div>
</template>
