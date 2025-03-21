<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck } from "@fortawesome/free-solid-svg-icons";
import { type AxiosError } from "axios";
import { BFormInput } from "bootstrap-vue";
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import { createWorkflow } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";

import AsyncButton from "@/components/Common/AsyncButton.vue";
import Heading from "@/components/Common/Heading.vue";

library.add(faCheck);

interface Pros {
    showHeading: boolean;
}

defineProps<Pros>();

const router = useRouter();

const workflowAnnotation = ref("");
const workflowName = ref("未命名工作流");
const workflowNameInput = ref<HTMLInputElement | null>(null);

async function onCreate() {
    try {
        const data = await createWorkflow(workflowName.value, workflowAnnotation.value);

        Toast.success(data.message);

        router.push(`/workflows/edit?id=${data.id}`);
    } catch (e) {
        const error = e as AxiosError<{ err_msg?: string }>;

        Toast.error(error.response?.data.err_msg ?? "不能创建工作流");
    }
}
</script>

<template>
    <div>
        <Heading v-if="!showHeading" h1 separator size="xl">创建工作流</Heading>

        <label for="workflow-name-input" class="font-weight-bold">工作流名称</label>
        <BFormInput
            id="workflow-name-input"
            ref="workflowNameInput"
            v-model="workflowName"
            class="mb-2"
            type="text"
            placeholder="输入工作流名称"
            description="工作流名称"
            @keyup.enter="() => onCreate()" />

        <label for="workflow-annotation-input" class="font-weight-bold">工作流注释</label>
        <BFormInput
            id="workflow-annotation-input"
            v-model="workflowAnnotation"
            class="mb-2"
            type="text"
            placeholder="输入工作流注释">
        </BFormInput>

        <div class="float-right">
            <AsyncButton
                variant="primary"
                :icon="faCheck"
                title="创建工作流"
                :disabled="workflowName.length === 0"
                :action="() => onCreate()">
                创建
            </AsyncButton>
        </div>
    </div>
</template>
