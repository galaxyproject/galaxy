<script setup lang="ts">
import axios, { type AxiosError } from "axios";
import { computed, ref, type Ref } from "vue";
import { withPrefix } from "@/utils/redirect";
import { getRedirectOnImportPath } from "../redirectPath";
import LoadingSpan from "@/components/LoadingSpan.vue";
import { useRouter } from "vue-router/composables";

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
        ? "You must provide a workflow archive URL or file."
        : sourceURL.value
        ? "Import workflow from URL"
        : "Import workflow from File";
});

const hasErrorMessage = computed(() => {
    return errorMessage.value != null;
});

const router = useRouter();

async function submit(ev: SubmitEvent) {
    ev.preventDefault();
    const formData = new FormData();

    if (sourceFile.value) {
        formData.append("archive_file", sourceFile.value);
    }

    if (sourceURL.value) {
        formData.append("archive_source", sourceURL.value);
    }

    loading.value = true;

    try {
        const response = await axios.post(withPrefix("/api/workflows"), formData);
        const path = getRedirectOnImportPath(response.data);

        router.push(path);
    } catch (error) {
        const message = (error as AxiosError).response?.data && (error as AxiosError).response?.data.err_msg;
        errorMessage.value = message || "Import failed for an unknown reason.";
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <b-form class="mt-4" @submit="submit">
        <h2 class="h-sm">Import from a Galaxy workflow export URL or a workflow file</h2>
        <b-form-group label="Archived Workflow URL">
            <b-form-input
                id="workflow-import-url-input"
                v-model="sourceURL"
                aria-label="Workflow Import URL"
                type="url" />
            If the workflow is accessible via a URL, enter the URL above and click Import.
        </b-form-group>
        <b-form-group label="Archived Workflow File">
            <b-form-file v-model="sourceFile" :accept="acceptedWorkflowFormats" />
            If the workflow is in a file on your computer, choose it and then click Import.
        </b-form-group>
        <b-alert :show="hasErrorMessage" variant="danger">{{ errorMessage }}</b-alert>
        <b-alert v-if="loading" show variant="info">
            <LoadingSpan message="Loading your workflow, this may take a while - please be patient." />
        </b-alert>
        <b-button
            id="workflow-import-button"
            type="submit"
            :disabled="isImportDisabled"
            :title="importTooltip"
            variant="primary">
            Import workflow
        </b-button>
    </b-form>
</template>
