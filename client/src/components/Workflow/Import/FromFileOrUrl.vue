<script setup lang="ts">
import axios from "axios";
import { BAlert, BButton, BForm, BFormGroup, BFormInput } from "bootstrap-vue";
import { computed, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { getRedirectOnImportPath } from "@/components/Workflow/redirectPath";
import { withPrefix } from "@/utils/redirect";

import LoadingSpan from "@/components/LoadingSpan.vue";

const loading = ref(false);
const sourceURL: Ref<string | null> = ref(null);
const sourceFile: Ref<string | null> = ref(null);
const errorMessage: Ref<string | null> = ref(null);
const acceptedWorkflowFormats = ".ga, .yml";

const isImportDisabled = computed(() => {
    return !sourceFile.value && !sourceURL.value;
});

const importTooltip = computed(() => {
    return isImportDisabled.value
        ? "您必须提供工作流归档URL或文件。"
        : sourceURL.value
        ? "从URL导入工作流"
        : "从文件导入工作流";
});

const hasErrorMessage = computed(() => {
    return errorMessage.value != null;
});

function autoAppendJson(urlString: string): string {
    const sharedWorkflowRegex = /^(https?:\/\/[\S]+\/u\/[\S]+\/w\/[^\s/]+)\/?$/;
    const matches = urlString.match(sharedWorkflowRegex);
    const bareUrl = matches?.[1];

    if (bareUrl) {
        return `${bareUrl}/json`;
    } else {
        return urlString;
    }
}

const router = useRouter();

async function submit(ev: SubmitEvent) {
    ev.preventDefault();
    const formData = new FormData();

    if (sourceFile.value) {
        formData.append("archive_file", sourceFile.value);
    }

    if (sourceURL.value) {
        const url = autoAppendJson(sourceURL.value);
        formData.append("archive_source", url);
    }

    loading.value = true;

    try {
        const response = await axios.post(withPrefix("/api/workflows"), formData);
        const path = getRedirectOnImportPath(response.data);

        router.push(path);
    } catch (error) {
        let message = null;
        if (axios.isAxiosError(error)) {
            message = error.response?.data?.err_msg;
        }
        errorMessage.value = message || "导入失败，原因未知。";
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <BForm class="mt-4 workflow-import-file" @submit="submit">
        <h2 class="h-sm">从Galaxy工作流导出URL或工作流文件导入</h2>

        <BFormGroup label="工作流归档URL">
            <BFormInput
                id="workflow-import-url-input"
                v-model="sourceURL"
                aria-label="工作流导入URL"
                type="url" />
            如果工作流可通过URL访问，请在上方输入URL并点击导入。
        </BFormGroup>

        <BFormGroup label="工作流归档文件">
            <b-form-file v-model="sourceFile" :accept="acceptedWorkflowFormats" />
            如果工作流在您计算机上的文件中，请选择文件然后点击导入。
        </BFormGroup>

        <BAlert :show="hasErrorMessage" variant="danger">
            {{ errorMessage }}
        </BAlert>

        <BAlert v-if="loading" show variant="info">
            <LoadingSpan message="正在加载您的工作流，这可能需要一些时间 - 请耐心等待。" />
        </BAlert>

        <BButton
            id="workflow-import-button"
            type="submit"
            :disabled="isImportDisabled"
            :title="importTooltip"
            variant="primary">
            导入工作流
        </BButton>
    </BForm>
</template>
