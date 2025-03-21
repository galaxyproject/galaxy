<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { onMounted, ref } from "vue";

import { GalaxyApi } from "@/api";
import { type StoredWorkflowDetailed } from "@/api/workflows";
import { rethrowSimple } from "@/utils/simple-error";

import GridInvocation from "../Grid/GridInvocation.vue";
import LoadingSpan from "../LoadingSpan.vue";

interface Props {
    storedWorkflowId: string;
}
const props = defineProps<Props>();

const loading = ref(true);
const workflow = ref<StoredWorkflowDetailed>();

onMounted(async () => {
    try {
        const { data, error } = await GalaxyApi().GET("/api/workflows/{workflow_id}", {
            params: { path: { workflow_id: props.storedWorkflowId } },
        });

        if (error) {
            rethrowSimple(error);
        }

        workflow.value = data;
    } finally {
        loading.value = false;
    }
});
</script>

<template>
    <GridInvocation
        v-if="!loading && workflow"
        :filtered-for="{
            type: 'StoredWorkflow',
            id: workflow.id,
            name: workflow.name,
        }" />
    <BAlert v-else-if="loading" variant="info" show>
        <LoadingSpan message="正在加载工作流的调用记录" />
    </BAlert>
    <BAlert v-else variant="danger" show>
        <p>无法加载ID为以下的存储工作流：{{ props.storedWorkflowId }}</p>
    </BAlert>
</template>
