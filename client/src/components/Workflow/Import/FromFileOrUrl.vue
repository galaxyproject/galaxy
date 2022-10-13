<script setup>
import axios from "axios";
import { computed, ref } from "vue";
import { safePath } from "utils/redirect";
import { redirectOnImport } from "../utils";
import LoadingSpan from "components/LoadingSpan";

const loading = ref(false);
const sourceURL = ref(null);
const sourceFile = ref(null);
const errorMessage = ref(null);
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

const submit = (ev) => {
    ev.preventDefault();
    const formData = new FormData();
    formData.append("archive_file", sourceFile.value);
    formData.append("archive_source", sourceURL.value);
    loading.value = true;
    axios
        .post(safePath("/api/workflows"), formData)
        .then((response) => {
            redirectOnImport(safePath("/"), response.data);
        })
        .catch((error) => {
            const message = error.response.data && error.response.data.err_msg;
            errorMessage.value = message || "Import failed for an unknown reason.";
        })
        .finally(() => {
            loading.value = false;
        });
};
</script>

<template>
    <b-form class="mt-4" @submit="submit">
        <h4>Import from a Galaxy workflow export URL or a workflow file</h4>
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
