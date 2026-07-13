<script lang="ts" setup>
import { BAlert } from "bootstrap-vue";
import { computed, ref, toRef } from "vue";

import type { FileSourceTemplateSummary, UserFileSourceModel } from "@/api/fileSources";
import { useConfigurationTemplateCreation } from "@/components/ConfigTemplates/useConfigurationTesting";

import { useGithubRepositoryOptions } from "./useGithubRepositoryOptions";

import ConfigurationMarkdown from "@/components/ObjectStore/ConfigurationMarkdown.vue";

const createUrl = "/api/file_source_instances";
const createTestUrl = "/api/file_source_instances/test";

interface CreateFormProps {
    template: FileSourceTemplateSummary;
    uuid?: string;
}
const props = defineProps<CreateFormProps>();
const title = computed(() => `Create a ${props.template.name} File Source`);

const emit = defineEmits<{
    (e: "created", fileSource: UserFileSourceModel): void;
}>();

// Track the live form values so dependent dropdowns (repo depends on the selected owner) update.
const formData = ref<Record<string, unknown>>({});
function onFormChange(incoming: Record<string, unknown>) {
    formData.value = incoming;
}

const { alertConditions, dynamicOptions } = useGithubRepositoryOptions(
    toRef(props, "template"),
    toRef(props, "uuid"),
    formData,
);

const formAlerts = computed(() => {
    const activeConditions = new Set(alertConditions.value);
    return (props.template.form_alerts ?? []).filter(
        (alert) => !alert.condition || activeConditions.has(alert.condition),
    );
});

const { ActionSummary, error, inputs, InstanceForm, onSubmit, submitTitle, loadingMessage, testRunning, testResults } =
    useConfigurationTemplateCreation(
        "file source",
        toRef(props, "template"),
        toRef(props, "uuid"),
        createTestUrl,
        createUrl,
        (fileSource: UserFileSourceModel) => emit("created", fileSource),
        dynamicOptions,
    );
</script>
<template>
    <div id="create-file-source-landing">
        <ActionSummary error-data-description="file-source-creation-error" :test-results="testResults" :error="error" />
        <BAlert v-for="alert in formAlerts" :key="alert.content" show :variant="alert.variant">
            <ConfigurationMarkdown :markdown="alert.content" :admin="true" />
        </BAlert>
        <InstanceForm
            :inputs="inputs"
            :title="title"
            :submit-title="submitTitle"
            :loading-message="loadingMessage"
            :busy="testRunning"
            @onChange="onFormChange"
            @onSubmit="onSubmit" />
    </div>
</template>
