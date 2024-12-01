<script setup lang="ts">
const VegaWrapper = () => import("@/components/Common/VegaWrapper.vue");
import { computed } from "vue";

const props = defineProps<{
    content: string;
}>();

const spec = computed(() => ({
    ...JSON.parse(props.content),
    width: "container",
}));
</script>

<template>
    <VegaWrapper :spec="spec" />
</template>
