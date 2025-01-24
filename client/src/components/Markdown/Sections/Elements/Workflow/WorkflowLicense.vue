<script setup lang="ts">
import License from "@/components/License/License.vue";

interface WorkflowLicenseProps {
    licenseId?: string;
}

defineProps<WorkflowLicenseProps>();
</script>

<template>
    <span>
        <License v-if="licenseId" :license-id="licenseId" />
        <p v-else>
            <i>Workflow does not define a license.</i>
        </p>
    </span>
</template>
