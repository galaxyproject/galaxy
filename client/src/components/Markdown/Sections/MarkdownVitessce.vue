<script setup lang="ts">
import { computed } from "vue";
import PluginContainer from "./Elements/PluginContainer.vue";

const props = defineProps<{
    content: string;
}>();

const spec = computed(() => ({
    ...JSON.parse(props.content),
}));
</script>

<template>
    <div>
        <PluginContainer plugin-src="/static/plugins/visualizations/vitessce/static/dist/index.js" />
        {{ spec }}
    </div>
</template>
