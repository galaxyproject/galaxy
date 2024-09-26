<script lang="ts" setup>
import { toRef } from "vue";

import type { FileSourceTemplateSummary, UserFileSourceModel } from "@/api/fileSources";
import { useConfigurationTemplateCreation } from "@/components/ConfigTemplates/useConfigurationTesting";

import { create, test } from "./services";

interface CreateFormProps {
    template: FileSourceTemplateSummary;
    uuid?: string;
}
const props = defineProps<CreateFormProps>();
const title = "Create a new file source for your data";

const emit = defineEmits<{
    (e: "created", fileSource: UserFileSourceModel): void;
}>();

const { ActionSummary, error, inputs, InstanceForm, onSubmit, submitTitle, loadingMessage, testRunning, testResults } =
    useConfigurationTemplateCreation(
        "file source",
        toRef(props, "template"),
        toRef(props, "uuid"),
        test,
        create,
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
