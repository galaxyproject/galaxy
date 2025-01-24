<script setup lang="ts">
import { computed, toRef } from "vue";

import { type FileSourceTemplateSummary, type UserFileSourceModel } from "@/api/fileSources";
import { useConfigurationTemplateUpgrade } from "@/components/ConfigTemplates/useConfigurationTesting";

import { useInstanceRouting } from "./routing";

const editTestUrl = "/api/file_source_instances/{uuid}/test";
const editUrl = "/api/file_source_instances/{uuid}";

interface Props {
    instance: UserFileSourceModel;
    latestTemplate: FileSourceTemplateSummary;
}

const props = defineProps<Props>();

const title = computed(() => `Upgrade File Source ${props.instance.name}`);

const {
    error,
    ActionSummary,
    inputs,
    InstanceForm,
    loadingMessage,
    onForceSubmit,
    onSubmit,
    testRunning,
    testResults,
    showForceActionButton,
    submitTitle,
} = useConfigurationTemplateUpgrade(
    "file source",
    toRef(props, "instance"),
    toRef(props, "latestTemplate"),
    editTestUrl,
    editUrl,
    useInstanceRouting
);
</script>
<template>
    <div>
        <ActionSummary error-data-description="file-source-upgrade-error" :test-results="testResults" :error="error" />
        <InstanceForm
            :inputs="inputs"
            :title="title"
            :submit-title="submitTitle"
            :loading-message="loadingMessage"
            :busy="testRunning"
            :show-force-action-button="showForceActionButton"
            @onForceSubmit="onForceSubmit"
            @onSubmit="onSubmit" />
    </div>
</template>
