<script setup lang="ts">
import { computed } from "vue";
import "./Elements/PluginWrapper";

const props = defineProps<{
    content: string;
}>();

const pluginData = computed(() => ({
    visualization_config: { 
        dataset_content: { ...JSON.parse(props.content) },
    }
}));
</script>

<template>
    <div>
        <plugin-wrapper plugin-name="vitessce" :plugin-data="JSON.stringify(pluginData)" height="500px"/>
    </div>
</template>
