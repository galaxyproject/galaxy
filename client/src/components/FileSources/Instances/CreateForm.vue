<script lang="ts" setup>
import { computed, toRef } from "vue";

import type { FileSourceTemplateSummary, UserFileSourceModel } from "@/api/fileSources";
import { useConfigurationTemplateCreation } from "@/components/ConfigTemplates/useConfigurationTesting";

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

const { ActionSummary, error, inputs, InstanceForm, onSubmit, submitTitle, loadingMessage, testRunning, testResults } =
    useConfigurationTemplateCreation(
        "file source",
        toRef(props, "template"),
        toRef(props, "uuid"),
        createTestUrl,
        createUrl,
        (fileSource: UserFileSourceModel) => emit("created", fileSource)
    );
</script>
<template>
    <div id="create-file-source-landing">
        <ActionSummary error-data-description="file-source-creation-error" :test-results="testResults" :error="error" />
        <InstanceForm
            :inputs="inputs"
            :title="title"
            :submit-title="submitTitle"
            :loading-message="loadingMessage"
            :busy="testRunning"
            @onSubmit="onSubmit" />
    </div>
</template>
