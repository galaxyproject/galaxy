<script setup lang="ts">
import { computed } from "vue";

const VegaWrapper = () => import("@/components/Common/VegaWrapper.vue");

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
