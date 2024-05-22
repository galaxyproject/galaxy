<script setup>
import { BCard } from "bootstrap-vue";
import { AVAILABLE_INVOCATION_EXPORT_PLUGINS } from "components/Workflow/Invocation/Export/Plugins";
import { useConfig } from "composables/config";

import InvocationExportPluginCard from "components/Workflow/Invocation/Export/InvocationExportPluginCard.vue";
import BioComputeObjectExportCard from "components/Workflow/Invocation/Export/Plugins/BioComputeObject/BioComputeObjectExportCard.vue";

const exportPlugins = AVAILABLE_INVOCATION_EXPORT_PLUGINS;

const { config } = useConfig(true);

defineProps({
    invocationId: {
        type: String,
        required: true,
    },
});
</script>

<template>
    <div v-if="config.enable_celery_tasks">
        <div v-for="(plugin, index) in exportPlugins" :key="index" class="mb-2">
            <InvocationExportPluginCard :export-plugin="plugin" :invocation-id="invocationId" />
        </div>
    </div>
    <div v-else>
        <!--
            WARNING
            This is temporal fix and should be dropped once Celery is the default task system in Galaxy.
            The task-based plugin system above should be used instead.
        -->
        <BCard title="BioCompute Object Export" class="export-plugin-card">
            <BioComputeObjectExportCard :invocation-id="invocationId" />
        </BCard>
    </div>
</template>
