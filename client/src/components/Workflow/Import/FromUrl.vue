<script setup lang="ts">
import axios from "axios";
import { BAlert, BForm, BFormGroup, BFormInput } from "bootstrap-vue";
import { computed, type Ref, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { useRouter } from "vue-router/composables";

import { getRedirectOnImportPath } from "@/components/Workflow/redirectPath";
import { withPrefix } from "@/utils/redirect";

import LoadingSpan from "@/components/LoadingSpan.vue";

const emit = defineEmits<{
    (e: "input-valid", valid: boolean): void;
}>();

const loading = ref(false);
const sourceURL: Ref<string | null> = ref(null);
const errorMessage: Ref<string | null> = ref(null);

const hasErrorMessage = computed(() => {
    return errorMessage.value != null;
});

// Validation state for wizard mode
const isValid = computed(() => {
    return sourceURL.value !== null && sourceURL.value.length > 0;
});

watch(isValid, (newValue) => {
    emit("input-valid", newValue);
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

async function submit() {
    const formData = new FormData();

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
        errorMessage.value = message || "Import failed for an unknown reason.";
    } finally {
        loading.value = false;
    }
}

// Expose method for wizard submit
async function attemptImport() {
    await submit();
}

defineExpose({ attemptImport });
</script>

<template>
    <BForm class="mt-4 workflow-import-url" @submit.prevent="submit">
        <h2 class="h-sm">Import from a Galaxy workflow export URL</h2>

        <BFormGroup label="Workflow Archive URL">
            <BFormInput
                id="workflow-import-url-input"
                v-model="sourceURL"
                aria-label="Workflow Import URL"
                type="url" />
            If your URL is from a workflow repository and doesn't end in <code>.ga</code>, you might need to use the
            <RouterLink to="/workflows/import?trs_url=Enter%20a%20TRS%20URL">TRS import method</RouterLink>
            instead.
        </BFormGroup>

        <BAlert :show="hasErrorMessage" variant="danger">
            {{ errorMessage }}
        </BAlert>

        <BAlert v-if="loading" show variant="info">
            <LoadingSpan message="Loading your workflow, this may take a while - please be patient." />
        </BAlert>
    </BForm>
</template>
