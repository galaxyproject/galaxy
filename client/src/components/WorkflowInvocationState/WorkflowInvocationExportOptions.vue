<script setup>
import InvocationExportPluginCard from "components/Workflow/Invocation/Export/InvocationExportPluginCard.vue";
import { AVAILABLE_INVOCATION_EXPORT_PLUGINS } from "components/Workflow/Invocation/Export/Plugins";

const exportPlugins = AVAILABLE_INVOCATION_EXPORT_PLUGINS;

defineProps({
    invocationId: {
        type: String,
        required: true,
    },
});
</script>

<template>
    <div>
        <div v-for="(plugin, index) in exportPlugins" :key="index" class="mb-2">
            <invocation-export-plugin-card :export-plugin="plugin" :invocation-id="invocationId" />
        </div>
    </div>
</template>
