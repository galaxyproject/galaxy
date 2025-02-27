<script setup lang="ts">
import axios from "axios";
import { ref, watch } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

import License from "@/components/License/License.vue";

interface WorkflowLicenseProps {
    workflowId: string;
}

const props = defineProps<WorkflowLicenseProps>();

const licenseId = ref("");

async function fetchLicense(workflowId: string) {
    try {
        const response = await axios.get(`${getAppRoot()}api/workflows/${workflowId}`);
        licenseId.value = response.data?.license || "";
    } catch (error) {
        console.error("Error fetching workflow license:", error);
        licenseId.value = "";
    }
}

watch(
    () => props.workflowId,
    () => fetchLicense(props.workflowId),
    { immediate: true }
);
</script>

<template>
    <span>
        <License v-if="licenseId" :license-id="licenseId" />
        <p v-else>
            <i>Workflow does not define a license.</i>
        </p>
    </span>
</template>
