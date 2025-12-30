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
const errorMessage: Ref<string | null> = ref(null);

const isImportDisabled = computed(() => {
    return !sourceURL.value;
});

const importTooltip = computed(() => {
    return isImportDisabled.value ? "You must provide a workflow archive URL." : "Import workflow from URL";
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
</script>

<template>
    <BForm class="mt-4 workflow-import-url" @submit="submit">
        <h2 class="h-sm">Import from a Galaxy workflow export URL</h2>

        <BFormGroup label="Archived Workflow URL">
            <BFormInput
                id="workflow-import-url-input"
                v-model="sourceURL"
                aria-label="Workflow Import URL"
                type="url" />
            If the workflow is accessible via a URL, enter the URL above and click Import.
        </BFormGroup>

        <BAlert :show="hasErrorMessage" variant="danger">
            {{ errorMessage }}
        </BAlert>

        <BAlert v-if="loading" show variant="info">
            <LoadingSpan message="Loading your workflow, this may take a while - please be patient." />
        </BAlert>

        <BButton
            id="workflow-import-button"
            type="submit"
            :disabled="isImportDisabled"
            :title="importTooltip"
            variant="primary">
            Import workflow
        </BButton>
    </BForm>
</template>
