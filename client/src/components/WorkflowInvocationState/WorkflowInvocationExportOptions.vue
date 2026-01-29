<script setup>
import { BCard } from "bootstrap-vue";
import { useConfig } from "composables/config";

import InvocationExportWizard from "@/components/Workflow/Invocation/Export/InvocationExportWizard.vue";
import BioComputeObjectExportCard from "@/components/Workflow/Invocation/Export/Plugins/BioComputeObject/BioComputeObjectExportCard.vue";

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
        <InvocationExportWizard :invocation-id="invocationId" />
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
