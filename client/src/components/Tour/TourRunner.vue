<script setup lang="ts">
import { useRouter } from "vue-router/composables";

import { runTour } from "./runTour";

import CenterFrame from "@/entry/analysis/modules/CenterFrame.vue";

const props = defineProps<{
    tourId: string;
}>();

const router = useRouter();

function routePush(path: string) {
    router.push(path);
}

runTour(props.tourId, null, routePush);
</script>

<template>
    <CenterFrame src="/welcome" />
</template>
