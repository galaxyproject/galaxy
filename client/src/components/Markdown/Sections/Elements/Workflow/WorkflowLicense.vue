<script setup lang="ts">
import { ref, watch } from "vue";

import { GalaxyApi } from "@/api";

import License from "@/components/License/License.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface WorkflowLicenseProps {
    workflowId: string;
}

const props = defineProps<WorkflowLicenseProps>();

const errorMessage = ref("");
const licenseId = ref("");
const loading = ref(true);

async function fetchLicense(workflowId: string) {
    loading.value = true;
    const { data, error } = await GalaxyApi().GET("/api/workflows/{workflow_id}", {
        params: {
            path: { workflow_id: workflowId },
        },
    });
    if (error) {
        errorMessage.value = `获取内容失败。${error.err_msg}`;
        licenseId.value = "";
    } else {
        errorMessage.value = "";
        licenseId.value = data?.license || "";
    }
    loading.value = false;
}

watch(
    () => props.workflowId,
    () => fetchLicense(props.workflowId),
    { immediate: true }
);
</script>

<template>
    <LoadingSpan v-if="loading" />
    <BAlert v-else-if="errorMessage" show variant="warning">{{ errorMessage }}</BAlert>
    <License v-else-if="licenseId" :license-id="licenseId" />
    <i v-else>工作流未定义许可证。</i>
</template>
